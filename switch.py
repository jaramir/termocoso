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

import socket
import traceback
import datetime

safe = datetime.timedelta( minutes=5 )

remote = ( "10.0.0.10", 1200 )
local = ( "10.0.0.100", 1200 )

msg_get = "secret,t=?"
msg_set_on = "secret,t=1"
msg_set_off = "secret,t=0"

timeout = 5

class TermoSwitch( object ):
    def __init__( self ):
        try:
            self.s = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
            self.s.bind( local )
            self.s.connect( remote )
            self.s.settimeout( timeout )
        except:
            traceback.print_exc()
        
        # salva orario attuale (per evitare cambiamento alla partenza)
        self.last = datetime.datetime.now()

    def get_state( self ):
        self.s.send( msg_get )
        received = self.s.recv( 10 )
        return received == "t=1"

    def set_state( self, state ):
        # non inviare se è inutile
        if self.get_state() == state:
            return
            
        # se non è passato il tempo di sicurezza non inviare
        if datetime.datetime.now() < ( self.last + safe ):
            return
            
        # invia messaggio e salva orario
        msg = msg_set_on if state else msg_set_off
        self.s.send( msg )
        self.s.recv( 10 )
        self.last = datetime.datetime.now()

