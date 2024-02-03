import panel as pn
import geopandas as gpd
import hvplot.pandas
import holoviews as hv
from holoviews.streams import Tap
from shapely.geometry import Point
from pathlib import Path
import datetime as dt
import os
import numpy as np
import pandas as pd

#region Local functions
def remove_bokeh_logo(plot, element):
    plot.state.toolbar.logo = None
#endregion

#region Load geometry data
#gdf = gpd.read_file('www/CA-discharge_basins_for_viz.gpkg') # No overlaps
gdf = gpd.read_file('www/CA-discharge_basins_plus.gpkg') # With overlaps

# Convert Multipolygons to Polygons, keeping the largest polygon
gdf['geometry'] = gdf['geometry'].apply(
    lambda x: max(x.geoms, key=lambda a: a.area) if x.geom_type == 'MultiPolygon' else x)

# Simplify geometry to reduce file size (tolerance in degrees)
gdf['geometry'] = gdf['geometry'].simplify(0.005)

# Make sure all relevant columns are strings
gdf['REGION'] = gdf['REGION'].astype(str)
gdf['BASIN'] = gdf['BASIN'].astype(str)
gdf['CODE'] = gdf['CODE'].astype(str)
gdf['gauges_RIVER'] = gdf['gauges_RIVER'].astype(str)

# Sort rows by area_km2 in descending order (plot smallest last)
gdf = gdf.sort_values('area_km2', ascending=False)
#endregion

# Create a StaticText widget
basin_code_widget = pn.widgets.StaticText(name='Basin Code', value='')
output = pn.pane.Str("Default message. Prints: Basin code and name upon click on a basin.")

#region Define panes
def plot_regional_map():
    # Plot the GeoDataFrame
    mapplot=gdf.hvplot(
        geo=True, tiles='OpenTopoMap',
        hover_cols=['CODE', 'gauges_RIVER'],
        line_width=1, line_color='black',
        tools=['tap', 'wheel_zoom'],
        alpha=0.7, c='REGION')\
        .opts(active_tools=['tap', 'wheel_zoom'],
              hooks=[remove_bokeh_logo],
              frame_height=400)
    return mapplot

# Create an impage pane with a default image
image_pane = pn.pane.PNG('png/16152_test.png')

# Message text pane
message_text_pane = pn.pane.Markdown("Please click on a basin in the map.",
        styles={'white-space': 'pre-wrap'})
#text_output = pn.Card(message_text_pane, title='Snow situation in the selected basin',
#            width=640)

#image_output = pn.Card(image_pane, title='Snow situation in the selected basin',
#                       width=640)

# Plot the map
map_regional = plot_regional_map()
map_subbasin = plot_regional_map()

# Toggle map view in a widget
view_options = pn.widgets.RadioButtonGroup(
    options=['Regional', 'Sub-basin'],
    value='Regional')

# Create a Tap stream
tap_regional = Tap(source=map_regional)
tap_subbasin = Tap(source=map_subbasin)
#endregion

#region Define the callback functions

# Upon click on a polygon, get the basin code
@pn.depends(tap_regional.param.x, tap_regional.param.y)
def get_region(x, y):
    try:
        # By default, the clicked point is in the Web Mercator projection (EPSG:3857)
        clicked_pointS = gpd.GeoSeries([Point(x, y)], crs="EPSG:3857")
        # Convert the GeoDataFrame to a projected CRS with meter units
        gdf_projected = gdf.to_crs("EPSG:32642")
        # Convert the clicked point to the same CRS
        clicked_point_transformedS = clicked_pointS.to_crs("EPSG:32642")
        clicked_point_transformed = clicked_point_transformedS[0]
        #output.object=f'gdf_projected.crs: {gdf_projected.crs}\nclicked_point_transformedS.crs: {clicked_point_transformedS.crs}'
        # Check if each polygon contains the clicked point
        contains = gdf_projected.contains(clicked_point_transformed)
        #output.object=output.object+f'\ncontains: {contains}'
        # Get the indices of all True values
        true_indices = np.argwhere(contains.values).flatten()
        #output.object=output.object+f'\ntrue_indices: {true_indices}'
        # Get the index of the last True value
        clicked_polygon_index = true_indices[-1] if len(true_indices) > 0 else None
        #output.object=output.object+f'\nclicked_polygon_index: {clicked_polygon_index}'
        # Get the polygon with the minimum distance
        clicked = gdf_projected.iloc[clicked_polygon_index]
        #output.object=output.object+f'\nclicked: {clicked}'
        region = clicked['REGION']
        print(output.object+f'\nRegion: {region}')
        return region
    except Exception as e:
        output.object=f'Error in get_region: \n   {e}'
        output.object=output.object+f'\n\nPlease click on a basin.'

@pn.depends(tap_subbasin.param.x, tap_subbasin.param.y)
def get_subbasin_code(x, y):
    try:
        # By default, the clicked point is in the Web Mercator projection (EPSG:3857)
        clicked_pointS = gpd.GeoSeries([Point(x, y)], crs="EPSG:3857")
        # Convert the GeoDataFrame to a projected CRS with meter units
        gdf_projected = gdf.to_crs("EPSG:32642")
        # Convert the clicked point to the same CRS
        clicked_point_transformedS = clicked_pointS.to_crs("EPSG:32642")
        clicked_point_transformed = clicked_point_transformedS[0]
        #output.object=f'gdf_projected.crs: {gdf_projected.crs}\nclicked_point_transformedS.crs: {clicked_point_transformedS.crs}'
        # Check if each polygon contains the clicked point
        contains = gdf_projected.contains(clicked_point_transformed)
        #output.object=output.object+f'\ncontains: {contains}'
        # Get the indices of all True values
        true_indices = np.argwhere(contains.values).flatten()
        #output.object=output.object+f'\ntrue_indices: {true_indices}'
        # Get the index of the last True value
        clicked_polygon_index = true_indices[-1] if len(true_indices) > 0 else None
        #output.object=output.object+f'\nclicked_polygon_index: {clicked_polygon_index}'
        # Get the polygon with the minimum distance
        clicked = gdf_projected.iloc[clicked_polygon_index]
        #output.object=output.object+f'\nclicked: {clicked}'
        basin_code = clicked['CODE']
        #basin_name = clicked['BASIN']
        print(output.object+f'\nBasin code: {basin_code}')
        return basin_code
    except Exception as e:
        output.object=f'Error in get_basin_code: \n   {e}'
        output.object=output.object+f'\n\nPlease click on a basin.'

@pn.depends(get_subbasin_code)
def get_river_name_for_basin(basin_code):
    try:
        # Get the river name for the basin
        river_name = gdf[gdf['CODE'] == basin_code]['gauges_RIVER'].values[0]
        return river_name
    except Exception as e:
        return f'Error in get_river_name_for_basin: \n   {e}'

@pn.depends(get_subbasin_code)
def read_current_data_for_basin(basin_code):
    try:
        # Read data from file with name <basin_code>_current.txt
        dfcurrent = pd.read_csv(f'data/{basin_code}_current.txt',
                                delimiter='\t')
        # Make sure the Date column is of type datetime
        dfcurrent['date'] = pd.to_datetime(dfcurrent['date'])
        output.object=output.object+f'\n\n{dfcurrent.head()}'
        return dfcurrent
    except Exception as e:
        return f'Error in read_current_data_for_basin: \n   {e}'

@pn.depends(get_subbasin_code)
def read_climate_data_for_basin(basin_code):
    try:
        # Read data from file with name <basin_code>_climate.txt
        dfclimate = pd.read_csv(f'data/{basin_code}_climate.txt',
                                delimiter='\t')
        # Make sure the Date column is of type datetime
        dfclimate['date'] = pd.to_datetime(dfclimate['date'])
        output.object=output.object+f'\n\n{dfclimate.head()}'
        return dfclimate
    except Exception as e:
        return f'Error in read_climate_data_for_basin: \n   {e}'

@pn.depends(tap_subbasin.param.x, tap_subbasin.param.y)
def plot_subbasin_data(x, y):
    try:
        # Read the basin code
        basin_code = get_subbasin_code(x, y)
        # Read the current data for the basin
        dfcurrent = read_current_data_for_basin(basin_code)
        #output.object=f'\n\n{dfcurrent.head()}'
        # Read the climate data for the basin
        dfclimate = read_climate_data_for_basin(basin_code)
        #output.object=output.object+f'\n\n{dfclimate.head()}'
        # Get river_name for basin
        river_name = get_river_name_for_basin(basin_code)
        # Plot the data using holoviews
        area_climate = hv.Area(
            dfclimate, vdims=['Q5_SWE', 'Q95_SWE'], label='Norm SWE range',
            kdims=['date']).opts(
                alpha=0.2, line_width=0, color='black')
        area_current = hv.Area(
            dfcurrent, vdims=['Q5_SWE', 'Q95_SWE'], label='Current SWE range',
            kdims=['date']).opts(
                alpha=0.2, line_width=0, color='red')
        curve_climate = hv.Curve(
            dfclimate, vdims=['Q50_SWE'], label='Norm SWE',
            kdims=['date']).opts(
                color='black')
        curve_current = hv.Curve(
            dfcurrent, vdims=['Q50_SWE'], label='Current SWE',
            kdims=['date']).opts(
                color='red')
        # Combine the plots
        fig = (area_climate * area_current * curve_climate * curve_current).opts(
            title=f'SWE situation for basin of river {river_name} (gauge {basin_code})',
            xlabel='Date', ylabel='SWE (mm)', height=400)
        fig.opts(hooks=[remove_bokeh_logo], responsive=True)
        return fig
    except Exception as e:
        return f'Error in plot_basin_data: \n   {e}'

@pn.depends(tap_regional.param.x, tap_regional.param.y)
def plot_region_data(x, y):
    try:
        # Read the basin code
        basin_code = get_region(x, y)
        # Read the current data for the basin
        dfcurrent = read_current_data_for_basin(basin_code)
        #output.object=f'\n\n{dfcurrent.head()}'
        # Read the climate data for the basin
        dfclimate = read_climate_data_for_basin(basin_code)
        #output.object=output.object+f'\n\n{dfclimate.head()}'
        # Adapt the name of the river basin for the title
        if basin_code == 'AMU_DARYA':
            basin_name = 'Amu Darya'
        elif basin_code == 'CHU_TALAS':
            basin_name = "Chu-Talas"
        elif basin_code == 'ISSYKUL':
            basin_name = 'Issykul'
        elif basin_code == 'MURGHAB_HARIRUD':
            basin_name = 'Murghab-Harirud'
        elif basin_code == 'SYR_DARYA':
            basin_name = 'Syr Darya'
        # Plot the data using holoviews
        area_climate = hv.Area(
            dfclimate, vdims=['Q5_SWE', 'Q95_SWE'], label='Norm SWE range',
            kdims=['date']).opts(
                alpha=0.2, line_width=0, color='black')
        area_current = hv.Area(
            dfcurrent, vdims=['Q5_SWE', 'Q95_SWE'], label='Current SWE range',
            kdims=['date']).opts(
                alpha=0.2, line_width=0, color='red')
        curve_climate = hv.Curve(
            dfclimate, vdims=['Q50_SWE'], label='Norm SWE',
            kdims=['date']).opts(
                color='black')
        curve_current = hv.Curve(
            dfcurrent, vdims=['Q50_SWE'], label='Current SWE',
            kdims=['date']).opts(
                color='red')
        # Combine the plots
        fig = (area_climate * area_current * curve_climate * curve_current).opts(
            title=f'SWE situation for the {basin_name} basin',
            xlabel='Date', ylabel='SWE (mm)', height=400)
        fig.opts(hooks=[remove_bokeh_logo], responsive=True)
        return fig
    except Exception as e:
        return f'Error in plot_basin_data: \n   {e}'

@pn.depends(view_options.param.value,
            tap_regional.param.x, tap_regional.param.y,
            tap_subbasin.param.x, tap_subbasin.param.y)
def get_snow_plot(value, xr, yr, xs, ys):
    try:
        if value == 'Regional':
            if xr is not None and yr is not None:
                return plot_region_data(xr, yr)
            else:
                return pn.pane.Str("<b>Please click on a basin.</b>")
        elif value == 'Sub-basin':
            if xs is not None and ys is not None:
                return plot_subbasin_data(xs, ys)
            else:
                return pn.pane.Markdown("<b>Please click on a basin.</b>")
    except Exception as e:
        return f'Error in get_snow_plot: \n   {e}'

# Define a function that returns the appropriate map plot based on the view option
@pn.depends(view_options.param.value)
def get_map_plot(value):
    try:
        if value == 'Regional':
            #output.object = output.object + f'\nMessage from get_map_plot\nview_option: {value}'
            return map_regional
        elif value == 'Sub-basin':
            #output.object = output.object +f'\nMessage from get_map_plot\nview_option: {value}'
            return map_subbasin
    except Exception as e:
        output.object = output.object + f'\nError in get_map_plot: \n   {e}'
        return output
#endregion


# Create a reactive object that updates based on the view option
#reactive_map_plot = pn.panel(pn.bind(get_map_plot, view_options))

# Add the callback
#tap_stream_regional = Tap(source=map_plot_regional)
#tap_stream_regional.param.watch_values(load_image, ['x', 'y'])

#tap_stream_subbasin = Tap(source=map_plot_subbasin)
#tap_stream_subbasin.param.watch_values(load_image_subbasin, ['x', 'y'])

# Define text for the dashboard
text_pane=pn.pane.Markdown(
    """
    Brought to you via the projects <a href='https://www.hydrosolutions.ch/projects/sapphire-central-asia' target='_blank'>SAPPHIRE Central Asia</a> & <a href='https://www.unifr.ch/geo/cryosphere/en/projects/smd4gc/cromo-adapt.html' target='_blank'>CHROMO-ADAPT</a>, funded by the <a href='https://www.eda.admin.ch/sdc' target='_blank'>Swiss Agency for Development and Cooperation (SDC)</a>, implemented by <a href='https://www.hydrosolutions.ch/' target='_blank'>hydrosolutions</a> and the <a href='https://www.slf.ch/en/' target='_blank'>Swiss Federal Institude for Snow and Avalanche Research (SLF)</a>. Last updated on """ + dt.datetime.now().strftime('%b %d, %Y') + "."
    )

refs = pn.Column(
    pn.pane.Markdown(" "),
    pn.pane.Markdown("Updated on the " + dt.datetime.now().strftime('%b %d, %Y') + " by:"),
    pn.Row(
        pn.pane.Image(os.path.join('www', 'logo_slf_color.svg'), height=50),
        pn.pane.Image(os.path.join('www', 'hydrosolutionsLogo.jpg'), height=50),
    ),
    pn.pane.Markdown("within the projects"),
    pn.pane.Image(os.path.join('www', 'sapphire_project_logo.jpg'), height=50),
    pn.pane.Markdown("funded by"),
    pn.pane.Image(os.path.join('www', 'sdc.jpeg'), height=50),
)

main_layout = pn.Column(
    # main_layout[0]
    pn.Card(get_map_plot,
            title='Tap a polygon to display the snow storage over time below',
            sizing_mode='stretch_width'),
    # main_layout[1]
    #text_output,
    pn.Card(get_snow_plot,
            title='Snow situation in the selected basin',
            sizing_mode='stretch_width'),
    # main_layout[2]
    text_pane)

# Create the dashboard
dashboard = pn.template.BootstrapTemplate(
    title='Snow Situation in Mountainous Central Asia',
    sidebar=[
        pn.pane.Markdown("<b>Select granularity of view:</b>\nRegional view: Show snow development in a regional basin.\nSub-basin view: Show snow development in a sub-basin."),
        view_options,
        pn.pane.Markdown(""),
        refs],
    main=main_layout,
    sidebar_width=220
)
dashboard.servable()

# panel serve dashboard.py --show --autoreload --port 5010