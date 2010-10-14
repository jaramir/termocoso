#!/usr/bin/python
# -*- coding: utf-8; -*-
#
# Copyright 2010 Francesco Gigli
#
# This file is part of Termocoso.
#
# Termocoso is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Termocoso is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import threading
import serial
import struct
import time
import os.path

device = "/dev/ttyUSB0"

class TermoFeed( threading.Thread ):
    # il nostro termometro emette una lettura ogni secondo
    # ogni quanti letture vogliamo fare la media e generare un punto?
    letture_per_punto = 10

    def __init__( self, callback ):
        threading.Thread.__init__( self )
        self.callback = callback
    
    def run( self ):
        self.stopthread = threading.Event()

        # letture grezze        
        letture = []

        # dato l'elenco delle letture grezze definisce una punto (lettura media)
        def average( values ):
            return sum( values ) / len( values )

        self.ser = False

        while not self.stopthread.isSet():
            # collegati al termometro
            if not self.ser and os.path.exists( device ):
                self.ser = serial.Serial( device, 19200, timeout=1 )
            
            # ritenta tra un secondo
            if not self.ser:                
                time.sleep( 1 )
                continue
        
            # leggi dal termometro
            buf = self.ser.readline()
            if len( buf ) != 4:
                continue
            
            data = struct.unpack( "BBBB", buf )
            
            t = ( float( data[0] ) * 256 + float( data[1] ) ) * 200 / 1023 - 50
            u = float( data[2] ) * 100 / 255
            
            letture.append( ( t, u ) )
            
            # se ci sono sufficenti letture calcola il punto
            if len( letture ) == self.letture_per_punto:
                temp_media = average( [ l[0] for l in letture ] )
                umid_media = average( [ l[1] for l in letture ] )
                letture = []
                
                # chiama la callback
                self.callback( temp_media, umid_media )

        # in uscita
        
        # spegni il termometro
        if self.ser:
            self.ser.close()
        
    def stop( self ):
        self.stopthread.set()

