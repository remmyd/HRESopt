# -*- coding: utf-8 -*-
"""
===============================================================================
                            TIME SERIES GENERATION FILE
===============================================================================
                            Most recent update:
                                4 June 2021
===============================================================================
Made by:
   Diane Remmy
Additional credits:
    Philip Sandwell, Iain Staffell, Stefan Pfenninger & Scot Wheeler
For more information, please email:
    diane.remmy@gmail.com
===============================================================================
"""
import requests
import sys
import os
import ast
import pandas as pd
import numpy as np
import json
from windpowerlib import ModelChain, WindTurbine, create_power_curve
from windpowerlib import data as wt

def gen_timeseries(location_file, location_data, demand_file, wind_turbine_file, gen_year = 2014):
    """
    Function:
        Saves Demand, PV and Wind Generation data as a named .csv file in the time series file
    Inputs:
        gen_year            (float or int)
    Outputs:
        .csv file of PV generation (kW/kWp) for the given year
    """

    time_dif = float(location_data.loc['Time difference'])
    wind_data = pd.read_excel(location_file, sheet_name='Wind Generation input', index_col=0, usecols=lambda x: x not in ['Unit'])
    # wind_data = pd.read_excel(location_file, sheet_name='Wind Generation input', index_col=0, header = None)[1]
    wind_height = wind_data.loc['height']

    #output = pd.DataFrame(columns = pd.MultiIndex(levels=[[]]*2, names=('number', 'color')))
    output = pd.DataFrame(columns = [['type'], ['number']])
    cols_to_use = ['Power (W)'] 
    df_demand = pd.read_csv(demand_file, usecols=cols_to_use, sep = ',').divide(1000) #demand is given in W but code works in kW
    output['Demand','1'] = df_demand['Power (W)']
    output["Solar",'1'] = get_local_time(get_solar_generation_from_RN(location_file,location_data,gen_year),time_difference = time_dif)
#    output[["Wind"]] = get_local_time(get_wind_data_from_RN(location_file,location_data,gen_year),time_difference = time_dif)['electricity']
    wind_speed = get_local_time(get_wind_data_from_RN(location_file,location_data,gen_year),time_difference = time_dif)['wind_speed']
    output['Wind Speed', str(wind_height[1])+'m'] = wind_speed
############# Test without generating wind profile ##############
    # wind_speed_file = "inputs/timeseries/wind_speed_Jocotan.csv"
    # df_wind_speed = pd.read_csv(wind_speed_file, header=[0,1])
    # df_wind_speed.index = df_wind_speed.index + 1
    # wind_speed = df_wind_speed["wind_speed"]["30"]
#####################################################################
    
    for wt in wind_data:
        output['Wind',wt] = get_wind_generation_from_windpowerlib(wind_speed, wind_data[wt], wind_turbine_file).divide(1000)    
    output.index += 1
    output.to_csv(timeseries_filepath + 'timeseries_' +str(location) +'_'+ str(wind_height[1])
                    +'m_'+ str(gen_year) + '.csv',index=False, sep = ',')

def get_local_time(data_UTC, time_difference = 0):
    """
    Function:
        Converts data from Renewables.ninja (kW/kWp and m/s in UTC time)
            to local time (user defined)
    Inputs:
    data_UTC      (Dataframe)
        time_difference     (Number, does not need to be integer)
    Outputs:
        output data (kW/kWp or m/s) in local time
    """
#   Round time difference to nearest hour (NB India, Nepal etc. do not do this)
    time_difference = round(time_difference)     
#   East of Greenwich
    if time_difference > 0:
        splits = np.split(data_UTC,[len(data_UTC)-time_difference])
        data_local = pd.concat([splits[1],splits[0]],ignore_index=True)
#   West of Greenwich 
    elif time_difference < 0:
        splits = np.split(data_UTC,[abs(time_difference)])
        data_local = pd.concat([splits[1],splits[0]],ignore_index=True)
#   No time difference, included for completeness
    else:
        data_local = data_UTC
    return data_local

def get_solar_generation_from_RN(location_file, location_data, year=2014):
#   Access information
    pv_data = pd.read_excel(location_file, sheet_name='PV Generation input', index_col=0, header = None)[1]
    api_base = 'https://www.renewables.ninja/api/'
    s = requests.session()
    url = api_base + 'data/pv'
    token = str(location_data.loc['token'])
    s.headers = {'Authorization': 'Token ' + token}

#   Gets some data from input file
    args = {
        'lat': float(location_data.loc['Latitude']),
        'lon': float(location_data.loc['Longitude']),
        'date_from': str(year)+'-01-01',
        'date_to': str(year)+'-12-31',
        'dataset': 'merra2',
        'capacity': 1, #kW
        'system_loss': float(pv_data.loc['system loss']),
        'tracking': 0,          
        'tilt': float(pv_data.loc['tilt']),
        'azim': float(pv_data.loc['azim']),
        'format': 'json',
#   Metadata and raw data now supported by different function in API
#            'metadata': False,
#            'raw': False
    }        
    r = s.get(url, params=args)
    
#   Parse JSON to get a pandas.DataFrame
    parsed_response = json.loads(r.text)
    df = pd.read_json(json.dumps(parsed_response['data']), orient='index')
    df = df.reset_index(drop=True)

    ##   Remove leap days
    if year in {2004,2008,2012,2016,2020}:
        feb_29 = (31+28)*24
        df = df.drop(range(feb_29,feb_29+24))
        df = df.reset_index(drop=True)
    return df

def get_wind_data_from_RN(location_file, location_data, year=2014):
    '''
    Function:
        Gets data from Renewables.ninja for a given year (kW/kWp) in UTC time
    Inputs:
        year                        (integer, from 2000-2016 inclusive)
        'PV generation inputs.csv'     (input file with location latitude, longitude,
                                            tilt angle and azimuth)
        token                       (API token )
    Outputs:
        WT output data in kW/kW installed in UTC time
    Notes:
        Need to convert to local time from UTC using get_local_time(...)
    '''
#   Access information
    wind_data = pd.read_excel(location_file, sheet_name='Wind Generation input', index_col=0, header = None)[1]
    api_base = 'https://www.renewables.ninja/api/'
    s = requests.session()
    url = api_base + 'data/wind'
    token = str(location_data.loc['token'])
    s.headers = {'Authorization': 'Token ' + token}

#   Gets some data from input file
    args = {
        'lat': float(location_data.loc['Latitude']),
        'lon': float(location_data.loc['Longitude']),
        'date_from': str(year)+'-01-01',
        'date_to': str(year)+'-12-31',
        'capacity': float(wind_data.loc['capacity']),
        'height': float(wind_data.loc['height']),
        'turbine': 'XANT M21 100',
        'format': 'json',
        'raw'   :  True
#   Metadata and raw data now supported by different function in API
#            'metadata': False,
#            'raw': False
    }        
    r = s.get(url, params=args)
    
#   Parse JSON to get a pandas.DataFrame
    parsed_response = json.loads(r.text)
    df = pd.read_json(json.dumps(parsed_response['data']), orient='index')
    df = df.reset_index(drop=True)
    
##   Remove leap days
    if year in {2004,2008,2012,2016,2020}:
        feb_29 = (31+28)*24
        df = df.drop(range(feb_29,feb_29+24))
        df = df.reset_index(drop=True)
    return df

################# wind profiles from windpowerlib ########################
def get_wind_generation_from_windpowerlib(wind_speed, wind_data, wind_turbine_file):

    weather = pd.DataFrame(wind_speed.index, columns = [['variable_name'], ['height']])
    weather = weather.set_index(weather.columns[0])
    weather['wind_speed', wind_data.loc['height']] = wind_speed.values
    weather['roughness_length', '0'] =[float(wind_data.loc['roughness_length'])] * len(weather.index)

    power_curve_library  = pd.read_csv(wind_turbine_file, engine = 'python')

    turbine_select = power_curve_library[power_curve_library['name'] == str(wind_data.loc['turbine_model'])]

    power = ast.literal_eval(turbine_select['power_curve_values'].values[0])
    power_wind_speed = ast.literal_eval(turbine_select['power_curve_wind_speed'].values[0])

    turbine = {
        'nominal_power': float(turbine_select['nominal_power'].values[0]),  # in W
        'hub_height': float(wind_data.loc['height']),  # in m
        'power_curve': pd.DataFrame(
                data={'value': power,  # in W
                    'wind_speed': power_wind_speed})  # in m/s
    }
    turbine = WindTurbine(**turbine)

    mc_turbine = ModelChain(turbine).run_model(weather)
    return mc_turbine.power_output
    
"""        
    def solar_degradation(self):
        lifetime = self.input_data.loc['lifetime']
        hourly_degradation = 0.20/(lifetime * 365 * 24)
        lifetime_degradation = []
        for i in range((20*365*24)+1):
            equiv = 1.0 - i * hourly_degradation
            lifetime_degradation.append(equiv)
        return pd.DataFrame(lifetime_degradation) 
"""
if __name__ == '__main__':
    location = 'Jocotan2'
    code_filepath = '/Users/redi/Workspace/test'
    timeseries_filepath = code_filepath + '/inputs/timeseries/'
    location_filepath = code_filepath + '/inputs/Locations/'
    location_file = location_filepath + location +'.xlsx'
    location_data = pd.read_excel(location_file, sheet_name='Location input', index_col=0, header = None)[1]
    demand_file = location_data.loc['demand_profile']
    wind_turbine_file = code_filepath + '/inputs/supply_small_wind_turbine_library.csv'
    

    gen_timeseries(location_file, location_data, demand_file, wind_turbine_file, location_data.loc['year'])
