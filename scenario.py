import time
import pandas as pd
from copy import deepcopy

from pyomo.core import Var, Param
from pyomo.opt import SolverFactory

from create_model import create_model


# function to get model parameter and variable values
def get_components(model, component_type):
   model_comp = model.component_map(ctype=component_type)
   serieses = []   # collection to hold the converted "serieses"
   series = []
   for k in model_comp.keys():   # this is a map of {name:ctype}
      c = model_comp[k]
      if len(c) == 1 and not str(k).startswith('WT') and not str(k).startswith('stg'):
      #if len(c) == 1 and not str(k).startswith('WT'):
         s = pd.DataFrame([float(c.extract_values()[None])], columns = [''])
         s.columns = pd.MultiIndex.from_tuples([(k, t) for t in s.columns])
         series.append(s)
      else:
         if (str(k).startswith('WT') and len(c) == len(model.WT.ordered_data())) or (str(k).startswith('stg') and len(c) == len(model.Stg.ordered_data())):
         #if (str(k).startswith('WT') and len(c) == len(model.WT.ordered_data())):
            reform = {(k, key): [value] for key, value in c.extract_values().items()}
            s = pd.DataFrame(reform)
            #s.columns = [str(t) for t in s.columns]
            series.append(s)
         else:
            s = pd.Series(c.extract_values(), index=c.extract_values().keys())
            # if the series is multi-indexed we need to unstack it...
            if type(s.index[0]) == tuple:  # it is multi-indexed
               s = s.unstack(level=1)
               #s.columns = [str((k, t)) for t in s.columns]
               s.columns = pd.MultiIndex.from_tuples([(k, t) for t in s.columns])           
            else:
               s = pd.DataFrame(s, columns = pd.MultiIndex.from_tuples([(k, '')]))         # force transition from Series -> df
            serieses.append(s)
   df_comp = pd.concat(series, axis = 1)
   df_comps = pd.concat(serieses, axis=1)
   
   #dict[str(component_type.__name__)] = df_comp.to_dict('records')
   #dict[str(component_type.__name__)+'TS'] = df_comps.to_dict()

   return df_comp, df_comps

def solve_model(model, solver, gap = 0.01):

   opt = SolverFactory(solver) # Solver use during the optimization

#    opt.set_options('Method=2 Crossover=0 BarConvTol=1e-4 OptimalityTol=1e-4 FeasibilityTol=1e-4 IterationLimit=1000') # !! only works with GUROBI solver   
   opt.set_options('Method=2')

   print('Calling solver...')
   results = opt.solve(model, tee=True) # Solving a model instance 
   print('Model solved')

   return results

def run_scenario(scenario_data, key, solver= 'gurobi'):

   # create model by defining the parameters and the variables
   start = time.time()                                     # Start time counter
   print("Model creation")
   model = create_model(scenario_data)   
   print("Model creation runtime:", time.time() - start)

   # run model
   start = time.time() 
   #results = solve_model(model, solver) 
   solve_model(model, solver)   
   print("Model runtime:", time.time() - start)

   # prepocessing results
   print("Output results")
#    dict_output = {}
#    dict_output = get_components(model, Param, dict_output)
#    dict_output = get_components(model, Var, dict_output)

   df_param, df_paramTS = get_components(model, Param)
   df_var, df_varTS = get_components(model, Var)

   df_result = pd.concat([df_param,df_var], axis = 1)
   df_result = df_result.set_index(pd.Index([key]))
   df_resultTS = pd.concat([df_paramTS,df_varTS], axis = 1)
   df_resultTS['Scenario'] = int(key)
   df_resultTS['Time_step'] = df_resultTS.index.astype(int)
   #df_resultTS = df_resultTS.set_index(['Scenario', 'Time_step'])

   return df_result, df_resultTS

