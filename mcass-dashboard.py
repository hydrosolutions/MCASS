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
import bokeh as bk
from dotenv import load_dotenv

# Load environment variables
res = load_dotenv()
if not res:
    raise ValueError("No .env file found")
# Read variables from environment
mcass_data_path = os.getenv('MCASS_DATA_PATH')

#region Local functions
def remove_bokeh_logo(plot, element):
    plot.state.toolbar.logo = None

def read_basin_geometry(filepath):
    """
    Read basin geometry from filepath (geopackage)

    Arguments:
        filepath (str) path to geopackage

    Return:
        geodataframe
    """
    #gdf = gpd.read_file('www/CA-discharge_basins_for_viz.gpkg') # No overlaps
    gdf = gpd.read_file(filepath) # With overlaps

    # Convert Multipolygons to Polygons, keeping the largest polygon
    gdf['geometry'] = gdf['geometry'].apply(
        lambda x: max(x.geoms, key=lambda a: a.area) if x.geom_type == 'MultiPolygon' else x)

    # Simplify geometry to reduce file size (tolerance in degrees)
    gdf['geometry'] = gdf['geometry'].simplify(0.01)

    # Make sure all relevant columns are strings
    gdf['REGION'] = gdf['REGION'].astype(str)
    gdf['BASIN'] = gdf['BASIN'].astype(str)
    gdf['CODE'] = gdf['CODE'].astype(str)
    gdf['gauges_RIVER'] = gdf['gauges_RIVER'].astype(str)

    # Initialize a column 'selecte' with False. Used to highlight selected basin
    # in the map. This column is updated by the basin selection widget.
    gdf['selected'] = False
    # Set the first basin to selected
    gdf.loc[0, 'selected'] = True

    # Replace gauges_RIVER=='None' with 'Name unknown'
    gdf['gauges_RIVER'] = gdf['gauges_RIVER'].replace('None', '<river name unknown>')

    # Create a column with labels for the basins
    gdf['label'] = gdf['CODE'] + ' - ' + gdf['gauges_RIVER']

    # Sort rows by area_km2 in descending order (plot smallest last)
    gdf = gdf.sort_values('area_km2', ascending=False)
    return gdf

def get_basin_selector_names_in_list(gdf):
    """
    Get the names of the basins for the basin selection widget and return them
    as a list

    Arguments:
        gdf (geodataframe) basin geometry

    Return:
        list of basin codes and basin names
    """
    gdf_for_names = gdf.sort_values(['REGION', 'CODE'], ascending=[True, True])
    options_list = list(gdf_for_names['label'].values)
    return options_list

def get_region_selector_names_in_list(gdf):
    """
    Get the names of the regions for the basin selection widget and return them
    as a list

    Arguments:
        gdf (geodataframe) basin geometry

    Return:
        list of regional river basins
    """
    gdf_for_names = gdf.sort_values(['REGION'], ascending=[True])

    options_list = list(gdf_for_names['REGION'].unique())
    return options_list

def update_gdf_with_selected_basin(selected_basin, view_option):
    """
    Update the selected basin in the GeoDataFrame. Does nothing if no basin is
    selected.

    Arguments:
        gdf (geodataframe): GeoDataFrame with basin geometries
        selected_basin (list): list of the selected basins

    Return:
        geodataframe with updated selected column
    """
    #print("DEBUG: calling update_gdf_with_selected_basin with selected_basin: ", selected_basin)
    #print("DEBUG: calling update_gdf_with_selected_basin with view_option: ", view_option)
    try:
        if selected_basin is not None and len(selected_basin) > 0:
            if view_option == 'Regional':
                # Set all basins to False
                gdf['selected'] = False
                # Set the selected basin to True only if it is not empty
                gdf.loc[gdf['REGION'] == selected_basin[0], 'selected'] = True
            else:
                # Set all basins to False
                gdf['selected'] = False
                # Set the selected basin to True only if it is not empty
                gdf.loc[gdf['label'] == selected_basin[0], 'selected'] = True
        return gdf
    except Exception as e:
        print(f'Error in update_gdf_with_selected_basin: \n   {e}')
        print(f'   Could not update selected_basin: {selected_basin}')
        return gdf


def update_basin_selection_widget_with_tap(view_option, xs, ys, xr, yr):
    #print("DEBUG: calling update_basin_selection_widget with xs, ys: ", xs, ys, xr, yr)
    # If the user clicked on the plot, select the basin at the clicked coordinates
    # Find the basin that contains the clicked point
    if view_option == 'Regional':
        clicked_basin_label = get_region_from_tap(xr, yr)
    else:
        clicked_basin_label = get_subbasin_code_from_tap(xs, ys)

    if clicked_basin_label is not None:
        # Update the value of the MultiChoice widget
        basin_selection.value = [clicked_basin_label]

#@pn.depends(tap_subbasin.param.x, tap_subbasin.param.y)
def get_subbasin_code_from_tap(x, y):
    #print("DEBUG: calling get_subbasin_code_from_tap with x, y: ", x, y)
    if x is not None or y is not None:
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
        #print("DEBUG: clicked['label']: ", clicked['label'])
        basin_code = clicked['label']
        #basin_name = clicked['BASIN']
        return basin_code
    return None

def get_region_from_tap(x, y):
    #print("DEBUG: calling get_regional_code_from_tap with x, y: ", x, y)
    if x is not None or y is not None:
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
        #print("DEBUG: clicked['REGION']: ", clicked['REGION'])
        basin_code = clicked['REGION']
        #basin_name = clicked['BASIN']
        return basin_code
    return None


def get_river_name_for_basin(basin_code):
    try:
        # Get the river name for the basin
        river_name = gdf[gdf['CODE'] == basin_code]['gauges_RIVER'].values[0]
        return river_name
    except Exception as e:
        return f'Error in get_river_name_for_basin: \n   {e}'

def read_current_data_for_basin(basin_code):
    try:
        # Read data from file with name <basin_code>_current.txt
        filename = os.path.join(mcass_data_path, f'{basin_code}_current.txt')
        dfcurrent = pd.read_csv(filename,
                                delimiter='\t')
        # Make sure the Date column is of type datetime
        dfcurrent['date'] = pd.to_datetime(dfcurrent['date'])
        return dfcurrent
    except Exception as e:
        return f'Error in read_current_data_for_basin: \n   {e}'

def read_previous_year_data_for_basin(basin_code):
    try:
        # Read data from file with name <basin_code>_current.txt
        filename = os.path.join(mcass_data_path, f'{basin_code}_previous.txt')
        dfprevious = pd.read_csv(filename,
                                delimiter='\t')
        # Make sure the Date column is of type datetime
        dfprevious['date'] = pd.to_datetime(dfprevious['date'])
        # Add 1 year to the date
        dfprevious['date'] = dfprevious['date'] + pd.DateOffset(years=1)
        return dfprevious
    except Exception as e:
        return f'Error in read_previous_year_data_for_basin: \n   {e}'

def read_climate_data_for_basin(basin_code):
    try:
        # Read data from file with name <basin_code>_climate.txt
        filename = os.path.join(mcass_data_path, f'{basin_code}_climate.txt')
        dfclimate = pd.read_csv(filename,
                                delimiter='\t')
        # Make sure the Date column is of type datetime
        dfclimate['date'] = pd.to_datetime(dfclimate['date'])
        return dfclimate
    except Exception as e:
        return f'Error in read_climate_data_for_basin: \n   {e}'


#endregion
custom_hover = bk.models.HoverTool(
    tooltips=[('Sub-basin', '@label')],)

filepath = 'www/CA-discharge_basins_plus.gpkg'
gdf = read_basin_geometry(filepath)

basins_list = get_basin_selector_names_in_list(gdf)
regions_list = get_region_selector_names_in_list(gdf)

# Create a StaticText widget
basin_code_widget = pn.widgets.StaticText(name='Basin Code', value='')
output = pn.pane.Str("Default message. Prints: Basin code and name upon click on a basin.")

# Toggle variable in a widget
variable_options = pn.widgets.RadioButtonGroup(
    options=['SWE', 'HS'],
    value='SWE',
    margin=(-10, 5, 5, 10))  # (top, right, bottom, left), default: (10, 5, 10, 5

# Toggle map view in a widget
view_options = pn.widgets.RadioButtonGroup(
    options=['Regional', 'Sub-basin'],
    value='Regional',
    margin=(-10, 5, 5, 10))  # (top, right, bottom, left), default: (10, 5, 10, 5)

# Select a basin
basin_selection = pn.widgets.MultiChoice(
    name='Delet selection, choose basin:',
    options=regions_list,
    value=[regions_list[0]],
    max_items=1,
    sizing_mode='stretch_width',
    margin=(-20, 5, 5, 10)  # (top, right, bottom, left), default: (10, 5, 10, 5)
    )

# Create empty Tap streams
tap_regional = Tap()
tap_subbasin = Tap()

#region Define panes
@pn.depends(basin_selection.param.value, view_options.param.value)
def plot_regional_map(selected_basin, view_option): #image_height):
    #print("DEBUG: calling plot_regional_map with selected_basin: ", selected_basin)
    # Define the height of the map
    image_height = 600

    # Update the selected column in the GeoDataFrame
    gdf = update_gdf_with_selected_basin(selected_basin, view_option)
    # Print gdf where selected == True
    #print("DEBUG: gdf[gdf['selected']==True]: ", gdf[gdf['selected']==True])

    # Plot the GeoDataFrame
    mapplot=gdf.hvplot(
        geo=True, tiles='EsriReference',
        hover_cols=['label'],
        line_width=1, line_color='black',
        tools=[custom_hover, 'tap', 'wheel_zoom'],
        alpha=0.7, c='REGION',
        legend = True)\
        .opts(active_tools=['tap', 'wheel_zoom'],
              hooks=[remove_bokeh_logo],
              #frame_height=image_height,
              min_height=image_height,
              aspect='equal',
              responsive=True)

    if len(selected_basin) == 1:
        # Plot the selected basin in red on top of the map
        selected_polygon_plot = gdf[gdf['selected']==True].hvplot(
            geo=True, line_color='white', line_width=1, fill_color=None,
            legend=True, tools=['tap', 'wheel_zoom'])

        mapplot = mapplot * selected_polygon_plot

        mapplot.opts(active_tools=['tap', 'wheel_zoom'],
                     min_height=image_height,
                     aspect='equal',
                     responsive=True)

    if view_option == 'Regional':
        tap_regional.source = mapplot
    else:
        tap_subbasin.source = mapplot

    #print("DEBUG: returning mapplot from plot_regional_map")
    return mapplot

@pn.depends(view_options.param.value, basin_selection.param.value,
            tap_subbasin.param.x, tap_subbasin.param.y,
            tap_regional.param.x, tap_regional.param.y)
def dynamically_update_map(view_option, selected_basin, xs, ys, xr, yr):
    # Test if view_option is consistent with the basin selection options
    #print("DEBUG: dynamically_update_map with ...")
    #print("       view_option: ", view_option)
    #print("       selected_basin: ", selected_basin)
    # Update the basin selection widget
    update_basin_selection_widget_with_tap(view_option, xs, ys, xr, yr)
    selected_basin = basin_selection.value
    #print("DEBUG: dynamically_update_map with selected_basin, xs, ys, xr, yr: ", selected_basin, xs, ys, xr, yr)
    # Update the map
    plot = plot_regional_map(selected_basin, view_option)
    #print("DEBUG: returning plot from dynamically_update_map")
    return plot

# Define a function that returns the appropriate map plot based on the view option
@pn.depends(view_options.param.value)
def get_map_plot(value):
    try:
        if value == 'Regional':
            map_regional = pn.panel(dynamically_update_map, sizing_mode='stretch_both')
            #tap_regional.source = map_regional.object
            #output.object = output.object + f'\nMessage from get_map_plot\nview_option: {value}'
            return map_regional
        elif value == 'Sub-basin':
            map_subbasin = pn.panel(dynamically_update_map, sizing_mode='stretch_both')
            #map_subbasin = pn.panel(plot_regional_map, sizing_mode='stretch_both')
            #tap_subbasin.source = map_subbasin.object
            #output.object = output.object +f'\nMessage from get_map_plot\nview_option: {value}'
            return map_subbasin
    except Exception as e:
        output.object = output.object + f'\nError in get_map_plot: \n   {e}'
        return output

#region Define the callback functions
@pn.depends(view_options.param.value, watch=True)
def update_basin_selection_widget_with_region_selection(view_option):
    #print("DEBUG: calling update_basin_selection_widget_with_region_selection with region_selection: ", view_option)
    # If view_option is 'Regional', update the basin selection widget
    if view_option == 'Regional':
        basin_selection.options = regions_list
        basin_selection.value = [regions_list[0]]
    else:
        basin_selection.options = basins_list
        basin_selection.value = [basins_list[37]]




@pn.depends(variable_options.param.value,
            basin_selection.param.value)
def plot_subbasin_data(variable, basin):
    try:
        # Read the basin code
        #basin_code = get_subbasin_code(x, y)
        basin_code = basin[0].split(' - ')[0]
        # Read the current data for the basin
        dfcurrent = read_current_data_for_basin(basin_code)
        #output.object=f'\n\n{dfcurrent.head()}'
        # Read previous year data for the basin
        dfprevious = read_previous_year_data_for_basin(basin_code)
        # Read the climate data for the basin
        dfclimate = read_climate_data_for_basin(basin_code)
        #output.object=output.object+f'\n\n{dfclimate.head()}'
        # Get river_name for basin
        river_name = get_river_name_for_basin(basin_code)
        # Plot the data using holoviews
        if variable == 'SWE':
            area_climate = hv.Area(
                dfclimate, vdims=['Q5_SWE', 'Q95_SWE'], label='Norm SWE range',
                kdims=['date']).opts(
                    alpha=0.2, line_width=0, color='black')
            curve_climate = hv.Curve(
                dfclimate, vdims=['Q50_SWE'], label='Norm',
                kdims=['date']).opts(
                color='black', tools=['hover'])
            curve_previous = hv.Curve(
                dfprevious, vdims=['Q50_SWE'], label='Previous year',
                kdims=['date']).opts(
                    color='green', tools=['hover'])
            curve_current = hv.Curve(
                dfcurrent, vdims=['Q50_SWE'], label='Current year',
                kdims=['date']).opts(
                    color='red', tools=['hover'])
            title_str = f'SWE situation for basin of river {river_name} (gauge {basin_code})'
            ylabel_str = 'SWE (mm)'
        else:
            area_climate = hv.Area(
                dfclimate, vdims=['Q5_HS', 'Q95_HS'], label='Norm HS range',
                kdims=['date']).opts(
                    alpha=0.2, line_width=0, color='black')
            curve_climate = hv.Curve(
                dfclimate, vdims=['Q50_HS'], label='Norm HS',
                kdims=['date']).opts(
                color='black', tools=['hover'])
            curve_previous = hv.Curve(
                dfprevious, vdims=['Q50_HS'], label='Previous HS',
                kdims=['date']).opts(
                    color='green', tools=['hover'])
            curve_current = hv.Curve(
                dfcurrent, vdims=['Q50_HS'], label='Current HS',
                kdims=['date']).opts(
                    color='red', tools=['hover'])
            title_str = f'HS situation for basin of river {river_name} (gauge {basin_code})'
            ylabel_str = 'HS (m)'
        # Combine the plots
        fig = (area_climate * curve_climate * curve_previous * curve_current)\
            .opts(
            title=title_str,
            xlabel='Date', ylabel=ylabel_str, height=600,
            hooks=[remove_bokeh_logo], responsive=True,
            active_tools=['wheel_zoom'])
        return fig
    except Exception as e:
        return f'Error in plot_basin_data: \n   {e}'

@pn.depends(variable_options.param.value,
            basin_selection.param.value)
def plot_region_data(variable, basin):
    try:
        # Read the basin code
        #basin_code = get_region(x, y)
        basin_code = basin[0].split(' - ')[0]
        # Read the current data for the basin
        dfcurrent = read_current_data_for_basin(basin_code)
        #output.object=f'\n\n{dfcurrent.head()}'
        # Read previous year data for the basin
        dfprevious = read_previous_year_data_for_basin(basin_code)
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
        if variable == 'SWE':
            area_climate = hv.Area(
                dfclimate, vdims=['Q5_SWE', 'Q95_SWE'], label='90%ile range',
                kdims=['date']).opts(
                    alpha=0.2, line_width=0, color='black')
            curve_climate = hv.Curve(
                dfclimate, vdims=['Q50_SWE'], label='Norm',
                kdims=['date']).opts(
                    color='black', tools=['hover'])
            curve_previous = hv.Curve(
                dfprevious, vdims=['Q50_SWE'], label='Previous year',
                kdims=['date']).opts(
                    color='green', tools=['hover'])
            curve_current = hv.Curve(
                dfcurrent, vdims=['Q50_SWE'], label='Current year',
                kdims=['date']).opts(
                    color='red', tools=['hover'])
            title_str = f'SWE situation for the {basin_name} basin'
            ylabel_str = 'SWE (mm)'
        # Combine the plots
        else:
            area_climate = hv.Area(
                dfclimate, vdims=['Q5_HS', 'Q95_HS'], label='90%ile range',
                kdims=['date']).opts(
                    alpha=0.2, line_width=0, color='black')
            curve_climate = hv.Curve(
                dfclimate, vdims=['Q50_HS'], label='Norm',
                kdims=['date']).opts(
                    color='black', tools=['hover'])
            curve_previous = hv.Curve(
                dfprevious, vdims=['Q50_HS'], label='Previous year',
                kdims=['date']).opts(
                    color='green', tools=['hover'])
            curve_current = hv.Curve(
                dfcurrent, vdims=['Q50_HS'], label='Current year',
                kdims=['date']).opts(
                    color='red', tools=['hover'])
            title_str = f'HS situation for the {basin_name} basin'
            ylabel_str = 'HS (m)'

        fig = (area_climate * curve_climate * curve_previous * curve_current).opts(
            title=title_str,
            ylabel=ylabel_str, xlabel='Date', height=600,
            hooks=[remove_bokeh_logo], responsive=True,
            active_tools=['wheel_zoom'])
        return fig
    except Exception as e:
        return f'Error in plot_basin_data: \n   {e}'

@pn.depends(view_options.param.value,
            variable_options.param.value,
            basin_selection.param.value)
def get_snow_plot(value, variable, basin):
    try:
        if value == 'Regional':
            #if xr is not None and yr is not None:
            return plot_region_data(variable, basin)
            #else:
            #    return pn.pane.Str("<b>Please click on a basin.</b>")
        elif value == 'Sub-basin':
            #if xs is not None and ys is not None:
            return plot_subbasin_data(variable, basin)
            #else:
            #    return pn.pane.Markdown("<b>Please click on a basin.</b>")
    except Exception as e:
        return f'Error in get_snow_plot: \n   {e}'

#endregion


# Define text for the dashboard
text_pane=pn.pane.Markdown(
    """
    Brought to you via the projects <a href='https://www.hydrosolutions.ch/projects/sapphire-central-asia' target='_blank'>SAPPHIRE Central Asia</a> & <a href='https://www.unifr.ch/geo/cryosphere/en/projects/smd4gc/cromo-adapt.html' target='_blank'>CROMO-ADAPT</a>, funded by the <a href='https://www.eda.admin.ch/sdc' target='_blank'>Swiss Agency for Development and Cooperation (SDC)</a>, implemented by <a href='https://www.hydrosolutions.ch/' target='_blank'>hydrosolutions</a> and the <a href='https://www.slf.ch/en/' target='_blank'>Swiss Federal Institude for Snow and Avalanche Research (SLF)</a>. Last updated on """ + dt.datetime.now().strftime('%b %d, %Y') + "."
    )

refs = pn.Column(
    pn.pane.Markdown(" "),
    pn.pane.Markdown("Updated on the " + dt.datetime.now().strftime('%b %d, %Y') + " by"),
    pn.Row(
        pn.pane.Image(os.path.join('www', 'logo_slf_color.svg'), height=50),
        pn.pane.Image(os.path.join('www', 'hydrosolutionsLogo.jpg'), height=50),
    ),
    pn.pane.Markdown("within the projects"),
    pn.Column(
        pn.pane.Image(os.path.join('www', 'chromoadapt_logo.png'), height=30),
        pn.pane.Image(os.path.join('www', 'sapphire_project_logo.jpg'), height=50),
    ),
    pn.pane.Markdown("funded by"),
    pn.pane.Image(os.path.join('www', 'sdc.jpeg'), height=50),
)

main_layout = pn.Column(
    # main_layout[0]
    pn.Card(pn.panel(get_map_plot),
            title='Tap a polygon to display the snow storage over time below',
            sizing_mode='stretch_width',
            collapsible=False),
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
        pn.pane.Markdown("<b>Select variable to display:</b>\nHS: Snow depth\nSWE: Snow water equivalent"),
        variable_options,
        pn.pane.Markdown("<b>Select granularity of view:</b>\nRegional view: Show snow development in a regional basin.\nSub-basin view: Show snow development in a sub-basin."),
        view_options,
        pn.pane.Markdown("<b>Search for sub-basin by hydropost code:</b>"),
        basin_selection,
        pn.pane.Markdown(""),
        refs],
    main=main_layout,
    sidebar_width=220
)
dashboard.servable()

# panel serve mcass-dashboard.py --show --autoreload --port 5010
