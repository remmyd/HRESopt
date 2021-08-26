import time
import pandas as pd
import numpy as np
from create_model import create_model
from scenario import run_scenario
from pyomo.core import Var, Param
#import cloudpickle
from copy import deepcopy

def remap_keys(mapping):
   return ({'key':k, 'value': v} for k, v in mapping.iteritems())

def get_scenario_data(s_data, s_param, s_type, s_value):
   if s_type == 'General':
      s_data[s_type][s_param] = s_data[s_type][s_param]*s_value
   else:
      s_data[s_type][s_param].update((x, y*s_value) for x, y in s_data[s_type][s_param].items())
   return s_data

# create input data dictionary
input_data = {}

# get input data files
input_file = "inputs/input_data_Jocotan_sensiBat.xlsx"
timeseries_file = "inputs/timeseries/timeseries_Jocotan2_30m_2015.csv"

# get location data
location_data = pd.read_excel(input_file, sheet_name='Location', index_col=0, header = None)[1]
input_data['Location'] = location_data.to_dict() # upload location data to dictionary

# set wind turbine power curve dictionary
# wind_turbine_file = code_filepath + '/inputs/supply_small_wind_turbine_library.csv'

# get wind speed and solar generation profile for case study


# get general input data as dictionary
df_general = pd.read_excel(input_file, sheet_name = 'General', usecols=lambda x: x not in ['Unit']).dropna()
general_data = df_general.set_index('Parameters')['Value'].to_dict()
input_data['General'] = general_data


# get wind turbine (WT) input data as dictionary
df_WT = pd.read_excel(input_file, sheet_name = 'Wind', index_col = 0, usecols=lambda x: x not in ['Unit'])       # get input data
df_WT = df_WT.transpose()
general_data['nWT_types'] = len(df_WT.index)
WT_data = df_WT.to_dict()
input_data['WT'] = WT_data

# get wind generation profile for different turbines


# get photovoltaic (pv) input data as dictionary
df_pv = pd.read_excel(input_file, sheet_name = 'PV', index_col = 0, usecols=lambda x: x not in ['Unit'])       # get input data
df_pv = df_pv.transpose()
general_data['nPV_types'] = len(df_pv.index)
pv_data = df_pv.to_dict()
input_data['PV'] = pv_data

# get storage input data as dictionary
df_stg = pd.read_excel(input_file, sheet_name = 'Storage', index_col = 0, usecols=lambda x: x not in ['Unit'])
df_stg = df_stg.transpose()
general_data['nStg_types'] = len(df_stg.index)
stg_data = df_stg.to_dict()
input_data['Storage'] = stg_data


# get generator input data as dictionary
df_GEN = pd.read_excel(input_file, sheet_name = 'Generator', index_col = 0, usecols=lambda x: x not in ['Unit'])
df_GEN = df_GEN.transpose()
general_data['nGEN_types'] = len(df_GEN.index)
GEN_data = df_GEN.to_dict()
input_data['Generator'] = GEN_data

# get input timeseries as dictionary
df_timeseries = pd.read_csv(timeseries_file, header = [0,1])
df_timeseries.index = df_timeseries.index + 1
df_timeseries = df_timeseries.drop(['type'], axis=1,level=0)

# select time series data only for evaluated days
df_timeseries = df_timeseries.iloc[0:24*general_data['evaluated_days']]

dict_ts = {}
dict_ts['Solar'] = df_timeseries[('Solar','1')].to_dict()
dict_ts['Demand'] = df_timeseries[('Demand','1')].to_dict()
df_wind = df_timeseries['Wind'].stack()
df_wind.index = df_wind.index.set_levels(df_wind.index.levels[1].astype(int), level=1)
dict_ts['Wind'] = df_wind.to_dict()
input_data.update(dict_ts)

#dict_scenarios = {}
#dict_scenarios[0] = run_scenario(input_data)
df_results = pd.DataFrame()
df_resultsTS = pd.DataFrame()

df_results, df_resultsTS = run_scenario(input_data, 0) # base scenario key = 0

# sensitivity
df_scenarios = pd.read_excel(input_file, sheet_name = 'Sensitivity_inputs', usecols = ['Parameter', 'Type','sensitivity_value'])
df_scenarios.index += 1
for s in df_scenarios.iterrows():
   s_id = s[0]
   s_data = deepcopy(input_data)
   s_data = get_scenario_data(s_data, s[1]['Parameter'], s[1]['Type'], s[1]['sensitivity_value'])
   #dict_scenarios[s_id] = run_scenario(s_data)
   df_results_scenario, df_resultsTS_scenario = run_scenario(s_data, s_id)
   df_results = df_results.append(df_results_scenario)
   df_resultsTS = df_resultsTS.append(df_resultsTS_scenario)

df_results.to_hdf('results/results.h5', key='df_results', format = 'table')
df_resultsTS.to_hdf('results/results.h5', key='df_resultsTS', format = 'table')

print(df_results.stg_capacity)
print(max(df_resultsTS.stg_SoC), min(df_resultsTS.stg_SoC))



# with open('results/test.pkl', mode='wb') as file:
#    cloudpickle.dump(model, file)

# with open('results/results.json', 'w') as fp:
#    json.dump(dict_scenarios, fp)

