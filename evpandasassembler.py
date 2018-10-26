#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 17 15:40:53 2018

@author: skoebric
"""

import geopandas as gpd
import pandas as pd
pd.options.mode.chained_assignment = None
from shapely.geometry import Point
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import folium
from folium import FeatureGroup

class EVPandasAssembler(object):
    def __init__(self):
        zips = gpd.read_file('/Users/skoebric/Dropbox/GitHub/CO EV Rates/COzips.geojson')
        zips = zips.rename({'ZCTA5CE10':'ZIP'}, axis = 'columns')
        zips['ZIP'] = zips['ZIP'].astype('int')
        
        regs = pd.read_csv('/Users/skoebric/Dropbox/GitHub/CO EV Rates/polk17_co_by_zip_fueltype.csv')
        
        PHEV = []
        HEV = []
        EV = []
        totals = []
        
        def regshybridlistmaker(row):
            zipc = row['ZIP']
            df_ = regs.loc[regs['ZIP'] == zipc]
            phev = df_.loc[df_['FUEL TYPE'] == 'PLUG IN HYBRID ELECTRIC VEHICLE']
            hev = df_.loc[df_['FUEL TYPE'] == 'HYBRID ELECTRIC VEHICLE']
            ev = df_.loc[df_['FUEL TYPE'] == 'ELECTRIC VEHICLE']
            total = df_['reg_cnt'].sum()
            outlist = []
            for df_ in [phev, hev, ev]:
                if len(df_) == 1:
                    outlist.append(int(df_['reg_cnt'][0:1]))
                elif len(df_) == 0:
                    outlist.append(0)
                else:
                    outlist.append('error')
                    print('error')
            totals.append(total)
            PHEV.append(outlist[0])
            HEV.append(outlist[1])
            EV.append(outlist[2])
                    
        zips.apply(regshybridlistmaker, axis = 1)
                        
        zips['PHEV'] = PHEV
        zips['HEV'] = HEV
        zips['EV'] = EV
        zips['total'] = totals
        
        zips['PHEVnorm'] = zips['PHEV']/ zips['total']
        zips['HEVnorm'] = zips['HEV']/ zips['total']
        zips['EVnorm'] = zips['EV']/ zips['total']
        
        def hexcolormapper(df, column, colorscale):
            norm = matplotlib.colors.Normalize(vmin=min(df[column]), vmax=max(df[column]), clip=False)
            mapper = plt.cm.ScalarMappable(norm=norm, cmap=colorscale)
            df[f'{column}_color'] = df[column].apply(lambda x: mcolors.to_hex(mapper.to_rgba(x)))
            return df
        
        zips = hexcolormapper(zips, 'HEV', plt.cm.Greens)
        zips = hexcolormapper(zips, 'PHEV', plt.cm.Reds)
        zips = hexcolormapper(zips, 'EV', plt.cm.Blues)
        zips = hexcolormapper(zips, 'HEVnorm', plt.cm.Greens)
        zips = hexcolormapper(zips, 'PHEVnorm', plt.cm.Reds)
        zips = hexcolormapper(zips, 'EVnorm', plt.cm.Blues)
        
        zips['PHEVnorm'] = round(zips['PHEVnorm']*100,2)
        zips['HEVnorm'] = round(zips['HEVnorm']*100,2)
        zips['EVnorm'] = round(zips['EVnorm']*100,2)
        self.zips = zips
        
        charg = pd.read_csv('/Users/skoebric/Dropbox/GitHub/CO EV Rates/alt_fuel_stations.csv', low_memory = False)
        charg = charg.loc[charg['State'] == 'CO']
        charg = charg[['Station Name','ZIP','Groups With Access Code','EV Level1 EVSE Num','EV Level2 EVSE Num','EV DC Fast Count','Latitude','Longitude']]
        charg['Station Name'] = [i.split(' -')[0] for i in charg['Station Name']]
        charg['ZIP'] = charg['ZIP'].astype(int)
        def latlonglister(row):
            lat = row['Latitude']
            long = row['Longitude']
            return [lat, long]
        charg['lat_long'] = charg.apply(latlonglister, axis = 1)
        
        level1chrg = charg.loc[charg['EV Level1 EVSE Num'] > 0]
        level2chrg = charg.loc[charg['EV Level2 EVSE Num'] > 0]
        dcfchrg = charg.loc[charg['EV DC Fast Count'] > 0]
        self.level1chrg = level1chrg
        self.level2chrg = level2chrg
        self.dcfchrg = dcfchrg
        
        coloradoshp = gpd.read_file('/Users/skoebric/Dropbox/shp files/cb_2017_us_state_5m/cb_2017_us_state_5m.shp')
        coloradoshp.crs = {'init':'epsg:4326'}
        coloradoshp = coloradoshp.loc[coloradoshp['STUSPS'] == 'CO']
        self.coloradoshp = coloradoshp
        
        xcelterritorygpd = gpd.read_file('/Users/skoebric/Documents/EV/Electric_Retail_Service_Territories/Electric_Retail_Service_Territories.shp')
        xcelterritorygpd = xcelterritorygpd.loc[xcelterritorygpd['NAME'] == 'PUBLIC SERVICE CO OF COLORADO']
        xcelterritorygpd = xcelterritorygpd[['geometry']]
        self.xcelterritorygpd = xcelterritorygpd
        
        transmissiongpd = gpd.read_file('/Users/skoebric/Documents/EV/Electric_Power_Transmission_Lines/Electric_Power_Transmission_Lines.shp')
        transmissiongpd = gpd.sjoin(transmissiongpd, coloradoshp, op='intersects')
        transmissiongpd = transmissiongpd[['OWNER','VOLT_CLASS','SUB_1','SUB_2','geometry']]
        self.transmissiongpd = transmissiongpd
    
    def mapper(self):
        m = folium.Map(location=[39.068305, -105.612593], zoom_start=7, tiles = 'stamentoner')
        folium.TileLayer('openstreetmap').add_to(m)
        
        level1_fg = FeatureGroup(name='Level 1 Chargers', show = False)
        level2_fg = FeatureGroup(name='Level 2 Chargers', show = False)
        dcfc_fg = FeatureGroup(name='DC Fast Chargers', show = True)
        hev_fg = FeatureGroup(name = 'Registered Hybrids', show = False)
        phev_fg = FeatureGroup(name = 'Registered PHEVs', show = False)
        ev_fg = FeatureGroup(name = 'Registered EVs', show = False)
        hevnorm_fg = FeatureGroup(name = 'Percent LDVs Hybrids', show = False)
        phevnorm_fg = FeatureGroup(name = 'Percent LDVs PHEVs', show = False)
        evnorm_fg = FeatureGroup(name = 'Percent LDVs EVs', show = True)
        transmission_fg = FeatureGroup(name = 'Transmission Lines', show = False)
        PSCo_fg = FeatureGroup(name = 'PSCo Territory', show = False)
        
        folium.GeoJson(self.xcelterritorygpd,
                      style_function = lambda feature: {
                          'fillColor' : '#B6174B',
                          'fillOpacity' : 0.3,
                          'color' :'#B6174B',
                          'weight' : 0.5
                      }).add_to(PSCo_fg)
        
        for index, row in self.transmissiongpd.iterrows():
            geojson_ = folium.GeoJson(self.transmissiongpd.loc[index:index+1],
                               style_function = lambda feature: {
                                   'fillColor':'#4863CE',
                                   'fillOpacity' : 0.3,
                                   'color':'#4863CE',
                                   'weight':2
                               })
            popup_ = folium.Popup(
                        f"<b>Owner:</b> {row['OWNER']}<br>"
                        f"<b>Volt Class:</b> {row['VOLT_CLASS']}<br>"
                        f"<b>Substations:</b> {row['SUB_1']} to {row['SUB_2']}<br>")
            popup_.add_to(geojson_)
            geojson_.add_to(transmission_fg)
        
        for index, row in self.zips.loc[self.zips['HEV'] > 0].iterrows():
            geojson_ = folium.GeoJson(self.zips.loc[index:index+1],
                              style_function = lambda feature: {
                                  'fillColor': feature['properties']['HEV_color'],
                                  'fillOpacity':0.5,
                                  'color': feature['properties']['HEV_color'],
                                  'opacity': 0.7,
                                  'weight':0.5}) 
                                            
            popup_ = folium.Popup(
                      f"<b>ZIP Code:</b> {int(row['ZIP'])}<br>"
                      f"<b>Num Hybrids:</b> {int(row['HEV'])}<br>"
                      f"<b>Num PHEVs:</b> {int(row['PHEV'])}<br>"
                      f"<b>Num EVs:</b> {int(row['EV'])}<br>"
                      )
            popup_.add_to(geojson_)
            geojson_.add_to(hev_fg)
        
        for index, row in self.zips.loc[self.zips['PHEV'] > 0].iterrows():
            geojson_ = folium.GeoJson(self.zips.loc[index:index+1],
                              style_function = lambda feature: {
                                  'fillColor': feature['properties']['PHEV_color'],
                                  'fillOpacity':0.3,
                                  'color': feature['properties']['PHEV_color'],
                                  'opacity': 0.5,
                                  'weight':0.5}) 
                                            
            popup_ = folium.Popup(
                      f"<b>ZIP Code:</b> {int(row['ZIP'])}<br>"
                      f"<b>Num Hybrids:</b> {int(row['HEV'])}<br>"
                      f"<b>Num PHEVs:</b> {int(row['PHEV'])}<br>"
                      f"<b>Num EVs:</b> {int(row['EV'])}<br>"
                      )
            popup_.add_to(geojson_)
            geojson_.add_to(phev_fg)
            
        for index, row in self.zips.loc[self.zips['EV'] > 0].iterrows():
            geojson_ = folium.GeoJson(self.zips.loc[index:index+1],
                              style_function = lambda feature: {
                                  'fillColor': feature['properties']['EV_color'],
                                  'fillOpacity':0.5,
                                  'color': feature['properties']['EV_color'],
                                  'opacity': 0.7,
                                  'weight':0.5}) 
                                            
            popup_ = folium.Popup(
                      f"<b>ZIP Code:</b> {int(row['ZIP'])}<br>"
                      f"<b>Num Hybrids:</b> {int(row['HEV'])}<br>"
                      f"<b>Num PHEVs:</b> {int(row['PHEV'])}<br>"
                      f"<b>Num EVs:</b> {int(row['EV'])}<br>"
                      )
            popup_.add_to(geojson_)
            geojson_.add_to(ev_fg)
            
        for index, row in self.zips.loc[self.zips['HEVnorm'] > 0].iterrows():
            geojson_ = folium.GeoJson(self.zips.loc[index:index+1],
                              style_function = lambda feature: {
                                  'fillColor': feature['properties']['HEVnorm_color'],
                                  'fillOpacity':0.5,
                                  'color': feature['properties']['HEVnorm_color'],
                                  'opacity': 0.7,
                                  'weight':0.5}) 
                                            
            popup_ = folium.Popup(
                      f"<b>ZIP Code:</b> {int(row['ZIP'])}<br>"
                      f"<b>Pct of LDVs Hybrids:</b> {row['HEVnorm']}%<br>"
                      f"<b>Pct of LDVs PHEVs:</b> {row['PHEVnorm']}%<br>"
                      f"<b>Pct of LDVs EVs:</b> {row['EVnorm']}%<br>"
                      )
            popup_.add_to(geojson_)
            geojson_.add_to(hevnorm_fg)
        
        for index, row in self.zips.loc[self.zips['PHEVnorm'] > 0].iterrows():
            geojson_ = folium.GeoJson(self.zips.loc[index:index+1],
                              style_function = lambda feature: {
                                  'fillColor': feature['properties']['PHEVnorm_color'],
                                  'fillOpacity':0.3,
                                  'color': feature['properties']['PHEVnorm_color'],
                                  'opacity': 0.5,
                                  'weight':0.5}) 
                                            
            popup_ = folium.Popup(
                      f"<b>ZIP Code:</b> {int(row['ZIP'])}<br>"
                      f"<b>Pct of LDVs Hybrids:</b> {row['HEVnorm']}%<br>"
                      f"<b>Pct of LDVs PHEVs:</b> {row['PHEVnorm']}%<br>"
                      f"<b>Pct of LDVs EVs:</b> {row['EVnorm']}%<br>"
                      )
            popup_.add_to(geojson_)
            geojson_.add_to(phevnorm_fg)
            
        for index, row in self.zips.loc[self.zips['EVnorm'] > 0].iterrows():
            geojson_ = folium.GeoJson(self.zips.loc[index:index+1],
                              style_function = lambda feature: {
                                  'fillColor': feature['properties']['EVnorm_color'],
                                  'fillOpacity':0.5,
                                  'color': feature['properties']['EVnorm_color'],
                                  'opacity': 0.7,
                                  'weight':0.5}) 
                                            
            popup_ = folium.Popup(
                      f"<b>ZIP Code:</b> {int(row['ZIP'])}<br>"
                      f"<b>Pct of LDVs Hybrids:</b> {row['HEVnorm']}%<br>"
                      f"<b>Pct of LDVs PHEVs:</b> {row['PHEVnorm']}%<br>"
                      f"<b>Pct of LDVs EVs:</b> {row['EVnorm']}%<br>"
                      )
            popup_.add_to(geojson_)
            geojson_.add_to(evnorm_fg)
            
        
        for index, row in self.level1chrg.iterrows():
            level1_fg.add_child(folium.CircleMarker(location= row['lat_long'],
                                                 radius = 4,
                                                 color = '#76B041', fill = True, fill_opacity = 0.8,
                                                 popup = (
                                                    f"<b>Num Level 1 Chargers:</b> {int(row['EV Level1 EVSE Num'])}<br>"
                                                 )))
        
        for index, row in self.level2chrg.iterrows():
            level2_fg.add_child(folium.CircleMarker(location= row['lat_long'],
                                             radius = 4,
                                             color = '#17BEBB', fill = True, fill_opacity = 0.8,
                                             popup = (
                                                f"<b>Num Level 2 Chargers:</b> {int(row['EV Level2 EVSE Num'])}<br>"
                                             )))
        
        for index, row in self.dcfchrg.iterrows():
            dcfc_fg.add_child(folium.CircleMarker(location= row['lat_long'],
                                             radius = 4,
                                             color = '#F9A03F', fill = True, fill_opacity = 0.8,
                                             popup = (
                                                f"<b>Num DC Fast Chargers:</b> {int(row['EV DC Fast Count'])}<br>"
                                             )))
        m.add_child(hev_fg)
        m.add_child(phev_fg)
        m.add_child(ev_fg)
        
        m.add_child(hevnorm_fg)
        m.add_child(phevnorm_fg)
        m.add_child(evnorm_fg)
        
        m.add_child(dcfc_fg)
        m.add_child(level1_fg)
        m.add_child(level2_fg)
        
        m.add_child(PSCo_fg)
        m.add_child(transmission_fg)
        
        m.add_child(folium.map.LayerControl(collapsed = False, autoZIndex = True))
        self.html = m
        return m
        
    def saver(self):
        self.html.save('/Users/skoebric/Dropbox/GitHub/CO EV Rates/index.html')