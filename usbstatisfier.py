#!/usr/bin/env python
from __future__ import division

import sys
import pcapy
import gflags
import re
import struct
from usbrevue import Packet
from PyQt4 import QtGui,QtCore
from PyQt4.QtGui import *
from PyQt4.QtCore import *

FLAGS = gflags.FLAGS

gflags.DEFINE_list('exp', None, 'A comma-separated list of expressions to be applied at data payload byte offsets. Offsets are referenced as "data[0], data[1], ...". Arithmetic operators (+, -, *, /), logical operators (and, or, not), and bitwise operators (^, &, |, !) are supported. For logical xor, use "bool(a) ^ bool(b)".')
gflags.DEFINE_boolean('verbose', False, 'Verbose mode; display the details of each packet modified.')


class Statisfier(object):
    def __init__(self, cmdline_exps):
        self.pcap = None
        self.out = None
        self.cmdline_exps = cmdline_exps

        # statisifer datas
        self.numPackets = 0;
        self.numTruePackets = 0;
        self.datamin = list()
        self.datamax = list()
     
        for exp in self.cmdline_exps:
          self.matches = re.finditer("data\[(\d+)\]", exp)
          sys.stderr.write(str(exp))

    def run(self):
        for packet in self.packet_generator('-'):
            self.commit_packet(packet)

    def packet_generator(self, input_stream='-'):
        self.pcap = pcapy.open_offline(input_stream)

        # create the Dumper object now that we have a Reader
        # self.out = self.pcap.dump_open('-')

        while True:
            (hdr, pack) = self.pcap.next()
            if hdr is None:
                return # EOF
            # keep track of the most recent yielding packet, for diffing
            self.orig_packet = Packet(hdr, pack)
            yield Packet(hdr, pack)

    def commit_packet(self, packet):
        self.apply_cmdline_exps(packet)
##############################################################
        # print out changes to each packet if --verbose
        if FLAGS.verbose:
            if self.isEquals:
               sys.stderr.write(str(self.numTruePackets))
               sys.stderr.write('/')
               sys.stderr.write(str(self.numPackets))
               sys.stderr.write('\n')

#!! NEEDS WORK. datamin and datamax need to reference correctly
            else:
               sys.stderr.write('NumPackets = ')
               sys.stderr.write(str(self.numPackets))
               sys.stderr.write('\n')

               print self.matches
               for match in self.matches:
                 sys.stderr.write(str(match.groups()))
                 sys.stderr.write(' Min = ')
                 sys.stderr.write(str(self.datamin[int(match.group(1))]))
                 sys.stderr.write(' Max = ')
                 sys.stderr.write(str(self.datamax[int(match.group(1))]))
                 sys.stderr.write('\n')

        if self.pcap is None:
            sys.stderr.write('Attempted to dump packets without first reading them -- make sure to call packet_generator()')
            sys.exit(1)
        else:
            if not sys.stdout.isatty():
                self.out.dump(packet.hdr, packet.datapack)

    def apply_cmdline_exps(self, packet):
        """Apply the expression supplied at the command line to a packet."""

        if self.cmdline_exps is not None:
            for exp in self.cmdline_exps:
                max_offset = 0 # highest offset needed to perfrm this expression

                # find max_offset
                numEquals = re.search("==",exp)
                if numEquals:
                   self.isEquals = True
                else:
                   self.isEquals = False


                if self.matches:
                    for match in self.matches:
                        if match.group(1) > max_offset:
                            max_offset = int(match.group(1))

                if self.isEquals:
                    self.numPackets += 1
                    if len(packet.data) > max_offset:
                        if eval(exp, {}, packet) is True:
                            self.numTruePackets += 1
                else: # isEquals == False
                    if len(self.datamin) < len(packet.data):
                       for num in range(len(packet.data) - len(self.datamin)):
                           self.datamin.append(99999)
                           self.datamax.append(0)

                    for match in self.matches:
                        if packet.data[int(match.group(1))] < self.datamin[int(match.group(1))]:
                            self.datamin[int(match.group(1))] = packet.data[int(match.group(1))]

                        if packet.data[int(match.group(1))] > self.datamax[int(match.group(1))]:
                            self.datamax[int(match.group(1))] = packet.data[int(match.group(1))]

                    self.numPackets += 1

    # accessors and mutators
    def set_cmdline_exp(self, exps):
        """Set the expression(s) meant to be passed in on the command line."""
        self.cmdline_exp = exps

def end_statisfier(num_modified):
    sys.stderr.write('\nSuccessfully modified ' + str(num_modified) + ' packets\n')
    sys.exit(0)



if __name__ == "__main__":
    # Open a pcap file from stdin, apply the user-supplied modification to
    # the stream, re-encode the packet stream, and send it to stdout.

    # Check if the user supplied a separate modification routine file (with the
    # --routine flag) and/or command line expression(s) (with the --exp flag)
    # At least one of these must be specified
    try:
        argv = FLAGS(sys.argv)
    except gflags.FlagsError:
        sys.stderr.write('There was an error parsing the command line arguments.Please use --help.')
        sys.exit(1)

    statisfier = Statisfier(FLAGS.exp)
    try:
        statisfier.run()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)


