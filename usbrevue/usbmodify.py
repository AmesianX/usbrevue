#!/usr/bin/env python
"""This is the USB Modifier module. It lets the user modify USB
packets programmatically by specifying one or more routines to be
applied to each packet in a pcap stream/file.

"""
from __future__ import division

import sys
import pcapy
import gflags
import re
import struct
from usbrevue import Packet
import traceback


FLAGS = gflags.FLAGS

gflags.DEFINE_string('routine', None, 'Filename containing your modification routine.')
gflags.DEFINE_list('exp', None, 'A comma-separated list of expressions to be applied at data payload byte offsets. Offsets are referenced as "data[0], data[1], ...". Arithmetic operators (+, -, *, /), logical operators (and, or, not), and bitwise operators (^, &, |, !) are supported. For logical xor, use "bool(a) ^ bool(b)".')
gflags.DEFINE_boolean('verbose', False, 'Verbose mode; display the details of each packet modified.')


class Modifier(object):
    """This class implements all modifier functionality. Does not
    interface with pcapy; instead, it expects to receive pcapy Reader
    and Dumper objects to work with.

    """
    def __init__(self, routine_file, cmdline_exps, pcap=None, out=None):
        self.pcap = pcap
        self.out = out
        self.routine_file = routine_file
        self.cmdline_exps = cmdline_exps
        self.num_modified = 0 # keep track of the number of modified packets

    def run(self):
        """Continuously read packets, apply the modification
        routine(s), and write out all packets, whether modified or
        not.

        """
        # continuously read packets, apply the modification routine, and write out
        while True:
            (hdr, pack) = self.pcap.next()
            if hdr is None:
                break # EOF
            packet = Packet(hdr, pack)

            # keep track of which parts of the packet, if any, are modified
            modified = {}
            for member in packet.fields:
                modified[member] = False
            orig_packet = packet.copy()
            self.apply_routine_file(packet)
            self.apply_cmdline_exps(packet)

            # figure out which parts of the packet were modified and print out
            # the changed parts (only with --verbose flag)
            notice_printed = False
            for member in packet.fields:
                if eval('packet.' + member) != eval('orig_packet.' + member):
                    self.num_modified += 1
                    if not notice_printed:
                        if FLAGS.verbose:
                            sys.stderr.write('Packet modified\n')
                            notice_printed = True
                    if FLAGS.verbose:
                        sys.stderr.write(str(eval('orig_packet.' + member)) + ' -> ' + str(eval('packet.' + member)) + '\n')
                        if notice_printed:
                            sys.stderr.write('\n')

            # pass all packets, modified or not, to the dumper
            try:
                modified_pack = packet.repack()
                if not sys.stdout.isatty():
                    out.dump(packet.hdr, modified_pack)
            except ValueError as valerr:
                sys.stderr.write('There was an error converting a packet to a binary string:\n')
                sys.stderr.write(str(valerr) + '\n')
                traceback.print_exc()
                sys.exit(1)


    def apply_routine_file(self, packet):
        """Apply the user-supplied external routine file to a packet."""
        if self.routine_file is not None:
            execfile(self.routine_file, {}, packet)


    def apply_cmdline_exps(self, packet):
        """Apply the expression supplied at the command line to a packet."""
        if self.cmdline_exps is not None:
            for exp in self.cmdline_exps:
                max_offset = 0 # highest offset needed to perform this expression

                # find max_offset
                matches = re.finditer(r"data\[(\d+)\]", exp)
                if matches:
                    for match in matches:
                        if match.group(1) > max_offset:
                            max_offset = int(match.group(1))

                if len(packet.data) > max_offset:
                    exec(exp, {}, packet)


    def check_valid_data(self, packet):
        """Check that the (possibly modified) packet attributes can
        still be converted to a pcap binary string. This behavior is
        already accomplished in the run() method; this function is
        just for unit testing.

        """

        try:
            packet.repack()
        except (ValueError, struct.error) as err:
            raise ValueError, "There was an error converting a packet to a binary string:\n" + err.message




    # accessors and mutators
    def get_num_modified(self):
        """Get the number of packets modified so far by the Modifier object."""
        return self.num_modified


    def set_routine_file(self, filestr):
        """Set the name of the user-supplied external routine file."""
        self.routine_file = filestr


    def set_cmdline_exp(self, exps):
        """Set the expression(s) meant to be passed in on the command line."""
        self.cmdline_exp = exps



def end_modifier(num_modified):
    """Display the number of modified packets (passed as parameter)
    and exit normally.

    """
    sys.stderr.write('\nSuccessfully modified ' + str(num_modified) + ' packets\n')
    sys.exit(0)



if __name__ == "__main__":
    # Open a pcap file from stdin, apply the user-supplied modification to
    # the stream, re-encode the packet stream, and send it to stdout.

    # Check if the user supplied a separate modification routine file (with the
    # --routine flag) and/or command line expression(s) (with the --exp flag). At
    # least one of these must be specified
    try:
        argv = FLAGS(sys.argv)
    except gflags.FlagsError:
        sys.stderr.write('There was an error parsing the command line arguments. Please use --help.')
        sys.exit(1)
    if FLAGS.routine is None and FLAGS.exp is None:
        sys.stderr.write('You must supply either a modification file, one or more command line expressions, or both.\n')
        sys.exit(1)

    pcap = pcapy.open_offline('-')
    if not sys.stdout.isatty():
        out = pcap.dump_open('-')
    else:
        out = None
    modifier = Modifier(FLAGS.routine, FLAGS.exp, pcap, out)
    try:
        modifier.run()
    except (KeyboardInterrupt, SystemExit):
        end_modifier(modifier.get_num_modified())

    end_modifier(modifier.get_num_modified())
