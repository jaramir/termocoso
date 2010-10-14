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

import datetime
import os.path
import pickle

class TermoStory( object ):
    def __init__( self, filename ):
        filename = filename.replace( ".db", "_pickle.db" )
        if os.path.exists( filename ):
            fp = open( filename, "r+" )
            self.data = pickle.load( fp )
            fp.close()
        else:
            self.data = []
        self.filename = filename
        
    def save( self ):
        fp = open( self.filename, "w+" )
        pickle.dump( self.data, fp )
        fp.close()

    def add( self, temperatura, umidita, stato ):
        point = ( datetime.datetime.now(), temperatura, umidita, stato )
        self.data.append( point )
        
    def search( self, dmin, dmax ):
        date = []
        temp = []
        umid = []
        switch = []
        for point in self.data:
            if point[0] >= dmin and point[0] <= dmax:
                date.append( point[0] )
                temp.append( point[1] )
                umid.append( point[2] )
                switch.append( point[3] )
        return date, temp, umid, switch

