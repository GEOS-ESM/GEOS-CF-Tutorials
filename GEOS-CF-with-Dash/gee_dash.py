"""
Helpful Links:
- https://dash-leaflet.herokuapp.com/#map_click

"""

import datetime as dt
import sys

import dash_leaflet as dl
from dash import Dash, html, Input, Output, dcc
import ee
import numpy as np
import pandas as pd
import plotly.express as px

ee.Initialize()

from gee_utils import ee_to_df

geosCf = ee.ImageCollection("NASA/GEOS-CF/v1/rpl/tavg1hr")
tropomi = ee.ImageCollection("COPERNICUS/S5P/NRTI/L3_NO2")

# Set selected bands
cfSurfBand = 'NO2' # mol mol-1
cfTropBand = 'TROPCOL_NO2' # 1.0e15 molec cm-2
tropNo2Band = 'tropospheric_NO2_column_number_density' # mol/m2

# Create band dictionaries to store unit conversion information
cf_chm_band_dict = {cfSurfBand: 1.0e9, cfTropBand: 10000*1e15/6.02e23, 'O3': 1.0e9, 'NOy': 1.0e9, 'PM25_RH35_GCC': 1}
cf_met_band_dict = {'T10M': 1, 'ZPBL': 1, 'U10M': 1, 'V10M': 1, 'RH': 1}
trop_band_dict = {tropNo2Band: 1}

# Change to exact lat/lon for takoma rec
lat = 38.97
lon = -77.02

# EE point from lat, lon
poi = ee.Geometry.Point(lon, lat)

#Number of days to visualize
num_days = 10

# Get subset GEE collection and subset Dataframe

# GEOS-CF Chemistry
cf_chm_subset = ee_to_df.ee_subset(cf_chm_band_dict, num_days)
cf_chm_subset_collection = cf_chm_subset.get_subset_collection(geosCf)

# GEOOS-CF Meteorology
cf_met_subset = ee_to_df.ee_subset(cf_met_band_dict, num_days)
cf_met_subset_collection = cf_met_subset.get_subset_collection(geosCf)

# TROPOMI chemistry
trop_subset = ee_to_df.ee_subset(trop_band_dict, num_days)
trop_subset_collection = trop_subset.get_subset_collection(tropomi)

# Mapping Set Up

# Select tropospheric NO2 and date range for GEOS-CF and scale to ppbv
img_date_start = dt.date.today() - dt.timedelta(num_days + 5)
img_date_start_str = img_date_start.strftime(format='%Y-%m-%d')
img_date_end = img_date_start + dt.timedelta(1)
img_date_end_str = img_date_end.strftime(format='%Y-%m-%d')

cf_trop_img = cf_chm_subset_collection.select(cfTropBand).filterDate(img_date_start_str, img_date_end_str).mean().multiply(cf_chm_band_dict[cfTropBand])

# Select tropospheric NO2 and date range for TROPOMI
trop_img = trop_subset_collection.filterDate(img_date_start_str, img_date_end_str).mean()

# Set visualization parameters for NO2
cf_vis_params = {
    'min': 1,'max': 40,
    'palette': ['white', 'purple'],
    'opacity': 0.5
}

# Visualization parameters for tropospheric column NO2
visTrop = {'min': 1e-6,
    'max': 1e-4,
    'palette': ['white', 'purple'],
    'opacity': 0.5
          }

def ee_tile_layer(ee_image_object, vis_params, name):
    """
    Adds a method for displaying Earth Engine image tiles to folium map.
    
    Parameters
        ----------
        ee_image_object : ee.image.Image
            GEE image collection to be subset
        vis_params : dict
            Dictionary of GEE visualization parameters
        
        Returns
        -------
        new_layer : dash-leaflet TileLayer
    """
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    new_layer = dl.TileLayer(
        url=map_id_dict['tile_fetcher'].url_format,
        attribution='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
        id=name
    )

    return new_layer

# Transform GEE images into leaflet tile layers
cf_ee_tiles = ee_tile_layer(cf_trop_img, visTrop, 'GEOS-CF-Tile')
trop_ee_tiles = ee_tile_layer(trop_img, visTrop, 'TROPOMI')

osm = dl.TileLayer(url='https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    maxZoom=19,
    attribution='© OpenStreetMap'
)

sel_marker = dl.LayerGroup(children = [
    dl.Marker(children=dl.Tooltip("({:.3f}, {:.3f})".format(*[lat, lon])), 
              position=[lat, lon])], 
              id="layer")

my_map = dl.Map(
            [
            dl.LayersControl(
            [dl.BaseLayer(osm, name='OSM', checked=True),
            dl.Overlay(cf_ee_tiles, name="GEOS-CF", checked=True, id='cf_layer'),
            dl.Overlay(children={}, name='TROPOMI', checked=True, id='tropomi_layer'),], id="lc"
            ),
            sel_marker],
            center=[lat, lon], zoom=10,
            style={'width': '100%', 'height': '50vh', 'margin': "auto", "display": "block", 'zIndex':1}, id="map")

# App Layout
app = Dash(__name__)
app.layout = html.Div([
    html.Div(className='row', children='GEOS-CF GEE Data Analysis Tool (GGdat?)',
             style={'textAlign': 'center', 'color': 'blue', 'fontSize': 30}),

    html.Div(dcc.DatePickerSingle(
        id='my-date-picker-single',
        min_date_allowed=cf_chm_subset.i_date,
        max_date_allowed=cf_chm_subset.f_date,
        #initial_visible_month=img_date_start + dt.timedelta(num_days//2),
        date=img_date_start + dt.timedelta(num_days//2),
        style={'zIndex':10}
    )),

    html.Div(id='output-container-date-picker-single'),

    my_map,

    html.Div(className='row', children=[
        html.Div(className='six columns', id='plot_area', children=dcc.Graph(figure={}, id='no2_timeseries'))
    ]),
])

@app.callback(
    [Output('output-container-date-picker-single', 'children'),
     Output('tropomi_layer', 'children'),
     Output('cf_layer', 'children')],
    Input('my-date-picker-single', 'date'))
def update_output(date_value):
    string_prefix = 'Map of Mean Tropospheric NO2 for: '

    if date_value is not None:
        date_object = dt.date.fromisoformat(date_value)
        date_string = date_object.strftime('%B %d, %Y')
        out_string = string_prefix + date_string

        img_date_start = date_object
        img_date_start_str = img_date_start.strftime(format='%Y-%m-%d')
        img_date_end = img_date_start + dt.timedelta(1)
        img_date_end_str = img_date_end.strftime(format='%Y-%m-%d')

        new_trop_img = trop_subset_collection.filterDate(img_date_start_str, img_date_end_str).mean()
        new_trop_layer = ee_tile_layer(new_trop_img, visTrop, 'TROPOMI')

        new_cf_img = cf_chm_subset_collection.select(cfTropBand)\
            .filterDate(img_date_start_str, img_date_end_str)\
                .mean()\
                    .multiply(cf_chm_band_dict[cfTropBand])
        new_cf_layer = ee_tile_layer(new_cf_img, visTrop, 'GEOS-CF-Tile')

        return out_string, new_trop_layer, new_cf_layer

@app.callback(Output("layer", "children"), [Input("map", "click_lat_lng")])
def map_click(click_lat_lng):
    if isinstance(click_lat_lng, list):
        pass
    else:
        click_lat_lng = [lat, lon]
    return [dl.Marker(children=dl.Tooltip("({:.3f}, {:.3f})".format(*click_lat_lng)), position=click_lat_lng)]

@app.callback(
    Output(component_id='no2_timeseries', component_property='figure'), 
    [Input("map", "click_lat_lng")]
)
def make_plot(click_lat_lng):
    if isinstance(click_lat_lng, list):
        pass
    else:
        click_lat_lng = [lat, lon]
    click_lat = click_lat_lng[0]
    click_lon = click_lat_lng[1]
    cf_chm_features = cf_chm_subset.get_point_df(geosCf, click_lat, click_lon)
    trop_features = trop_subset.get_point_df(tropomi, click_lat, click_lon)
    trop_features['datetime'] = pd.to_datetime(trop_features['datetime']).dt.round("H")

    merged = cf_chm_features.merge(trop_features,on='datetime', how='left')
    merged.fillna(value=np.nan, inplace=True)
    merged.rename(columns={cfTropBand: 'GEOS-CF', tropNo2Band: 'TROPOMI'}, inplace=True)
    melty = pd.melt(merged, id_vars='datetime', value_vars = ['GEOS-CF', 'TROPOMI'], var_name='NO2 Value Source')

    fig = px.scatter(data_frame=melty, 
                     x='datetime', 
                     y='value', 
                     color = 'NO2 Value Source', 
                     title = 'Tropospheric NO2 Timeseries for {:.3f}, {:.3f}'.format(*click_lat_lng))
    fig.update_yaxes(title= 'Tropospheric NO2 (mol/m^2)', exponentformat='e')

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)