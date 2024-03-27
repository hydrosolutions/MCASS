import pandas as pd
import glob

def get_all_subbasin_txt_files_that_contain_string(string):
    filelist = glob.glob(f'./data/*{string}*.txt')
    # Remove the files that do not contain numbers in the file name
    filelist = [file for file in filelist if any(char.isdigit() for char in file)]
    return filelist

def get_all_region_txt_files_that_contain_string(string):
    filelist = glob.glob(f'./data/*{string}*.txt')
    # Only keep files that do not conatin numbers in the file name
    filelist = [file for file in filelist if not any(char.isdigit() for char in file)]
    return filelist

def get_basin_id_from_file_path(file_path):
    # Gets basin id from a file path of the form './data/<basin_id>_current.txt'
    return file_path.split('/')[-1].split('_')[0]

def read_last_data_from_file_to_dataframe(file_path):
    basin_id = get_basin_id_from_file_path(file_path)
    # Read txt file into dataframe, select only the columns we need and rename
    # the columns to be more descriptive. Only read the last row of the file
    # as the other rows are not needed.
    data = pd.read_csv(file_path, delimiter='\t')
    data = data[['date', 'Q50_SWE', 'Q50_HS']]
    data['basin_id'] = basin_id
    # Only keep the last row of the data
    data = data.tail(1)
    return data

def read_data_for_date_from_file_to_dataframe(file_path, date):
    basin_id = get_basin_id_from_file_path(file_path)
    # Read txt file into dataframe, select only the columns we need and rename
    # the columns to be more descriptive. Only read the last row of the file
    # as the other rows are not needed.
    data = pd.read_csv(file_path, delimiter='\t')
    data = data[['date', 'Q5_SWE', 'Q5_HS', 'Q50_SWE', 'Q50_HS', 'Q95_SWE', 'Q95_HS']]
    data['basin_id'] = basin_id
    data = data[data['date'] == date]
    return data

def get_last_lines_from_subbasin_files_into_dataframe(string):
    all_files = get_all_subbasin_txt_files_that_contain_string(string)
    return pd.concat([read_last_data_from_file_to_dataframe(file) for file in all_files])

def get_lines_for_date_from_subbasin_files_into_dataframe(string, date):
    all_files = get_all_subbasin_txt_files_that_contain_string(string)
    return pd.concat([read_data_for_date_from_file_to_dataframe(file, date) for file in all_files])

def get_last_lines_from_region_files_into_dataframe(string):
    all_files = get_all_region_txt_files_that_contain_string(string)
    return pd.concat([read_last_data_from_file_to_dataframe(file) for file in all_files])

def get_lines_for_date_from_region_files_into_dataframe(string, date):
    all_files = get_all_region_txt_files_that_contain_string(string)
    return pd.concat([read_data_for_date_from_file_to_dataframe(file, date) for file in all_files])

def aggregate_subbasins_data(filepath_for_aggregated_data):
    # Get all the files that contain the string 'current'
    current_data = get_last_lines_from_subbasin_files_into_dataframe('current')
    # Rename the columns to be more descriptive
    current_data = current_data.rename(columns={'Q50_SWE': 'current_swe', 'Q50_HS': 'current_hs'})
    # Get the first date from the current data
    date = current_data['date'].iloc[0]
    # Get all the files that contain the string 'climate'
    climate_data = get_lines_for_date_from_subbasin_files_into_dataframe('climate', date)
    # Rename the columns to be more descriptive
    climate_data = climate_data.rename(columns={'Q50_SWE': 'climate_swe', 'Q50_HS': 'climate_hs'})
    # Merge the two dataframes on the 'basin_id' and 'date' columns
    data = pd.merge(current_data, climate_data, on=['basin_id', 'date'])
    # Set a flag if current SWE is above the 95 percentile of the climate SWE
    data['swe_threshold'] = 'normal'
    # If current swe is above the 95 percentile of the climate swe, set the
    # flag to 'high'
    data.loc[data['current_swe'] > data['Q95_SWE'], 'swe_threshold'] = 'high'
    data.loc[data['current_swe'] < data['Q5_SWE'], 'swe_threshold'] = 'low'

    # Same for the snow height
    data['hs_threshold'] = 'normal'
    data.loc[data['current_hs'] > data['Q95_HS'], 'hs_threshold'] = 'high'
    data.loc[data['current_hs'] < data['Q5_HS'], 'hs_threshold'] = 'low'
    # Save the data to a csv file
    data.to_csv(filepath_for_aggregated_data, index=False)

def aggregate_region_data(filepath_for_aggregated_data):
    # Get all the files that contain the string 'current'
    current_data = get_last_lines_from_region_files_into_dataframe('current')
    # Rename the columns to be more descriptive
    current_data = current_data.rename(columns={'Q50_SWE': 'current_swe', 'Q50_HS': 'current_hs'})
    # Get the first date from the current data
    date = current_data['date'].iloc[0]
    # Get all the files that contain the string 'climate'
    climate_data = get_lines_for_date_from_region_files_into_dataframe('climate', date)
    # Rename the columns to be more descriptive
    climate_data = climate_data.rename(columns={'Q50_SWE': 'climate_swe', 'Q50_HS': 'climate_hs'})
    # Merge the two dataframes on the 'basin_id' and 'date' columns
    data = pd.merge(current_data, climate_data, on=['basin_id', 'date'])
    # Set a flag if current SWE is above the 95 percentile of the climate SWE
    data['swe_threshold'] = 'normal'
    # If current swe is above the 95 percentile of the climate swe, set the
    # flag to 'high'
    data.loc[data['current_swe'] > data['Q95_SWE'], 'swe_threshold'] = 'high'
    data.loc[data['current_swe'] < data['Q5_SWE'], 'swe_threshold'] = 'low'

    # Same for the snow height
    data['hs_threshold'] = 'normal'
    data.loc[data['current_hs'] > data['Q95_HS'], 'hs_threshold'] = 'high'
    data.loc[data['current_hs'] < data['Q5_HS'], 'hs_threshold'] = 'low'
    # Save the data to a csv file
    data.to_csv(filepath_for_aggregated_data, index=False)

if __name__ == '__main__':
    aggregate_subbasins_data(filepath_for_aggregated_data='./data/subbasins_merged_data.csv')
    aggregate_region_data(filepath_for_aggregated_data='./data/regions_merged_data.csv')