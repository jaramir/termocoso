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

import os

import matplotlib
matplotlib.use('GTK')

from matplotlib.figure import Figure
from matplotlib.backends.backend_gtkagg import FigureCanvasGTKAgg as FigureCanvas

import matplotlib.dates
import matplotlib.ticker

import matplotlib.collections

import gtk
gtk.gdk.threads_init()

from story import TermoStory
from feed import TermoFeed
from config import TermoConfig

from switch import TermoSwitch

import datetime

import sys
prog = sys.argv[0]

prefix = ""
if "/" in prog:
    prefix = "/".join( prog.split( "/" )[:-1] ) + "/"
builder_file = prefix + "termocoso.xml"

def fmt_temp( temp ):
    return "%.2f°C" % temp
    
def fmt_umid( umid ):
    return "%.2f%%" % umid

temp_formatter = matplotlib.ticker.FormatStrFormatter( u"%.2f°C" )
umid_formatter = matplotlib.ticker.FormatStrFormatter( u"%.2f%%" )

modes = [ "acceso", "spento", "programmato" ]
default_mode = modes[1]

tolleranza = 0.25

graph_width = datetime.timedelta( hours=24 )
graph_margin = datetime.timedelta( minutes=15 )

class TermoGUI( object ):
    def __init__( self, basedir ):
        self.builder = gtk.Builder()
        self.builder.add_from_file( builder_file ) 
        
        self.config = TermoConfig( basedir + "config.db" )
        
        self.mode = self.config.get( "mode", default_mode )
        self.builder.get_object( "radio%s" % self.mode ).set_active( True )
        
        self.scales = []
        for i in range( 24 ):
            scale = self.builder.get_object( "vscale%s" % i )
            scale.set_value( self.config.get( "temp_%s" % i, 0 ) )
            self.scales.append( scale )
        
        self.builder.connect_signals( self )
        
        # collegati alla caldaia
        self.switch = TermoSwitch()
        self.update_switch_ui()
    
        # crea il thread del termometro
        # specifica la callback
        self.feed = TermoFeed( self.got_point )
        self.feed.start()
        
        # apre/crea lo storico
        self.storico = TermoStory( basedir + "storico.db" )
        
        # crea il grafico
        self.figure = Figure()
        self.canvas = FigureCanvas( self.figure )
        
        # crea asse temperatura
        self.temp_axes = self.figure.add_subplot( 111 )
        self.temp_axes.xaxis.set_major_locator( matplotlib.dates.HourLocator() )
        self.temp_axes.xaxis.set_minor_locator( matplotlib.dates.MinuteLocator() )
        self.temp_axes.xaxis.set_major_formatter( matplotlib.dates.DateFormatter( '%H' ) )
        self.temp_axes.set_ylabel( u"Temperatura", color="m" )
        self.temp_axes.yaxis.set_major_formatter( temp_formatter )
        self.temp_axes.grid( True )
        
        # crea asse umidita
        self.umid_axes = self.temp_axes.twinx()
        self.umid_axes.xaxis.set_major_locator( matplotlib.dates.HourLocator() )
        self.umid_axes.xaxis.set_minor_locator( matplotlib.dates.MinuteLocator() )
        self.umid_axes.xaxis.set_major_formatter( matplotlib.dates.DateFormatter( '%H' ) )
        self.umid_axes.set_ylabel( u"Umidità", color= "c" )
        self.umid_axes.yaxis.set_major_formatter( umid_formatter )
        self.umid_axes.grid( True )

        # crea linee
        self.temp_line = self.temp_axes.plot( [], [], "m" )[0]
        self.umid_line = self.umid_axes.plot( [], [], "c", alpha=0.5 )[0]
        self.switch_collection = None
        
        self.update_plot()

        hbox2 = self.builder.get_object( "hbox2" )
        hbox2.add( self.canvas )

        # partiamo
        self.builder.get_object( "window1" ).show_all()

    def on_mode_toggled( self, radio ):
        """ è stata cambiata la modalità..
        """
        for mode in modes:
            radio = self.builder.get_object( "radio%s" % mode )
            if radio.get_active():
                self.mode = mode
                self.config.set( "mode", mode )
                break
        # impostato su acceso/spento -> spegniamo/accendiamo il riscaldamento
        if mode == "acceso":
            self.switch.set_state( True )
        elif mode == "spento":
            self.switch.set_state( False )

    def on_vscale_value_changed( self, scale ):
        """ uno degli slider è stato spostato..
        """
        for idx, obj in enumerate( self.scales ):
            if obj == scale:
                self.config.set( "temp_%s" % idx, scale.get_value() )
                break
        else:
            raise Exception( "VScale non trovato" )

    def got_point( self, temp, umid ):
        """ abbiamo ricevuto una misurazione dal termometro..
        """
        # popola lo storico
        self.storico.add( temp, umid, self.switch.get_state() )
        
        # pilota la caldaia..
        if self.mode == "programmato":
            hh = datetime.datetime.now().hour
            temp_prog = self.config.get( "temp_%s" % hh, 0 )
            
            # versione grezza
            # temperatura attuale +- tolleranza -> attacca e stacca
            # utilizziamo solo la sicurezza interna dello switch
            if temp < temp_prog - tolleranza:
                self.switch.set_state( True )
            elif temp > temp_prog + tolleranza:
                self.switch.set_state( False )
        elif self.mode == "acceso":
            self.switch.set_state( True )
        elif self.mode == "spento":
            self.switch.set_state( False )
            
        # aggiorna la UI
        self.update_temp_umid( temp, umid )
        self.update_switch_ui()
    
    def update_switch_ui( self ):
        """ leggi lo stato dello switch e aggiorna la UI
        """
        label = self.builder.get_object( "label_switch" )
        state = self.switch.get_state() 
        if state == None:
            label.set_text( "N/A" )
        elif state:
            label.set_text( "Il riscaldamento è ACCESO" )
        else:
            label.set_text( "Il riscaldamento è SPENTO" )

    def update_plot( self ):
        """ leggi lo storico e aggiorna i grafici
        """
        dmax = datetime.datetime.now() + graph_margin
        dmin = dmax - ( graph_width + graph_margin )
        dates, temp, umid, switch = self.storico.search( dmin, dmax )

        mpldates = [ matplotlib.dates.date2num( date ) for date in dates ]
        mpldmin = matplotlib.dates.date2num( dmin )
        mpldmax = matplotlib.dates.date2num( dmax )
        
        if temp:
            # grafico delle temperature
            mintemp = min(temp)*0.999
            maxtemp = max(temp)*1.001
            self.temp_line.set_data( mpldates, temp )
            self.temp_axes.set_ylim( mintemp, maxtemp )
            self.temp_axes.set_xlim( mpldmin, mpldmax )
            
            # span della caldaia
            if self.switch_collection:
                self.switch_collection.remove()    
            self.switch_collection = matplotlib.collections.BrokenBarHCollection.span_where(
                mpldates, ymin=mintemp, ymax=maxtemp, where=switch, facecolor='red', alpha=0.1, linewidths=0 )
            self.temp_axes.add_collection( self.switch_collection )
            
        if umid:
            # grafico delle umidita (asse x condivisa)
            minumid = min(umid)*0.999
            maxumid = max(umid)*1.001
            self.umid_line.set_data( mpldates, umid )
            self.umid_axes.set_ylim( minumid, maxumid )
            self.umid_axes.set_xlim( mpldmin, mpldmax )
        
        self.canvas.draw()
        
    def update_temp_umid( self, temp, umid ):
        """ aggiorna le label della temperatura e umidità attuali
        """
        gtk.gdk.threads_enter()
        self.builder.get_object( "label_temp" ).set_text( fmt_temp( temp ) )
        self.builder.get_object( "label_umid" ).set_text( fmt_umid( umid ) )
        self.update_plot()        
        gtk.gdk.threads_leave()

    def on_window1_destroy( self, widget, data=None ):
        """ uscita dal programma
        """
        self.storico.save()
        self.config.save()
        self.feed.stop()
        gtk.main_quit()

if __name__ == "__main__":
    base = os.getenv( "HOME" ) + "/.termocoso/"
    if not os.path.exists( base ):
        os.mkdir( base )
    app = TermoGUI( base )
    gtk.main()

