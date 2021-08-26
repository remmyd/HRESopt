from pyomo.environ import Param, RangeSet, NonNegativeReals, Var, Set, Binary 
from pyomo.environ import ConcreteModel
from pyomo.environ import Objective, minimize, Constraint
from constraints import *
import time

def create_model(input_data):   
    model = ConcreteModel()

    "Project parameters"
    model.evaluated_days    = Param(within=NonNegativeReals, initialize = input_data['General']["evaluated_days"])
    model.timesteps         = Param(within=NonNegativeReals, initialize = input_data['General']["evaluated_days"]*24)                          # Number of periods of analysis of the energy variables
    model.delta_t           = Param(within=NonNegativeReals, initialize = input_data['General']["delta_time"])                          # Time step in hours
#    model.date_start        = Param(initialize = general_data["time_start"])                                                 # Start date of the analisis
    model.discount_rate     = Param(within=NonNegativeReals, initialize = input_data['General']["discount_rate"])                          # Discount rate of the project in %
    # model.project_cost_inv  = Param(within=NonNegativeReals, initialize = input_data['General']["project_cost_inv"])
    # model.project_cost_om   = Param(within=NonNegativeReals, initialize = input_data['General']["project_cost_om"])
    # model.project_lifetime  = Param(within=NonNegativeReals, initialize = input_data['General']["project_lifetime"])

    "Parameters of bi-directional inverter"
    model.BID_specific_cost_inv         = Param(within=NonNegativeReals, initialize = input_data['General']["BID_converter_specific_cost_inv"])
    model.inverter_cost_om              = Param(within=NonNegativeReals, initialize = input_data['General']["inverter_specific_cost_om"])
    model.inverter_efficiency           = Param(within=NonNegativeReals, initialize = input_data['General']["inverter_efficiency"])
    model.BID_lifetime                  = Param(within=NonNegativeReals, initialize = input_data['General']["BID_converter_lifetime"])
    model.rectifier_cost_om             = Param(within=NonNegativeReals, initialize = input_data['General']["rectifier_specific_cost_om"])
    model.rectifier_efficiency          = Param(within=NonNegativeReals, initialize = input_data['General']["rectifier_efficiency"])
    model.BID_max                       = Param(within=NonNegativeReals, initialize = 100)

    "Sets"
    model.Time  = RangeSet(1, model.timesteps)               # Set from 1 to number of timesteps to be simulated
    model.PV    = RangeSet(1, input_data['General']['nPV_types'])           # Set from 1 to the number of PV technologies to analized
    model.Stg   = RangeSet(1, input_data['General']['nStg_types'])          # Set from 1 to the number of storage types to analized
    model.WT    = RangeSet(1, input_data['General']['nWT_types'])           # Set from 1 to the number of WT technologies to analized
    model.GEN   = RangeSet(1, input_data['General']['nGEN_types'])           # Set from 1 to the number of GEN technologies to analized

    "Parameters of demand" 
    model.loads              = Param(model.Time, default=0, initialize=input_data['Demand']) # electricity load  
    model.loads_sum          = Param(default= 0, initialize=sum(input_data['Demand'].values()))

    model.NSL_max_allowed   = Param(within=NonNegativeReals, initialize = input_data['General']["NSL_max_allowed"])
    model.NSL_penalty_cost  = Param(within=NonNegativeReals, initialize = input_data['General']["NSL_penalty_cost"]) 
    
    "Parameters of PV" 
    model.pv_maxCap                     = Param(within=NonNegativeReals, initialize = input_data['PV']["pv_maxCap"][1])
    model.pv_specific_cost_inv          = Param(within=NonNegativeReals, initialize = input_data['PV']["pv_specific_cost_investment"][1])
    model.pv_cost_om                    = Param(within=NonNegativeReals, initialize = input_data['PV']["pv_specific_cost_om"][1])
    model.pv_lifetime                   = Param(within=NonNegativeReals, initialize = input_data['PV']["pv_lifetime"][1])
    model.pv_nominal_output             = Param(model.Time, within=NonNegativeReals, initialize=input_data['Solar'])

    "Parameters of PV" 
    model.WT_capacity                   = Param(model.WT, within=NonNegativeReals, initialize = input_data['WT']["WT_capacity"])
    model.WT_specific_cost_inv          = Param(model.WT, within=NonNegativeReals, initialize = input_data['WT']["WT_specific_cost_investment"])
    model.WT_cost_om                    = Param(model.WT, within=NonNegativeReals, initialize = input_data['WT']["WT_specific_cost_om"])
    model.WT_lifetime                   = Param(model.WT, within=NonNegativeReals, initialize = input_data['WT']["WT_lifetime"])
    model.WT_nominal_output             = Param(model.Time, model.WT, within=NonNegativeReals, initialize=input_data['Wind'])
    
    "Parameters of Storage"
    model.stg_specific_cost_inv     = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_specific_cost_investment"])
    model.stg_fixed_cost_inv        = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_fixed_cost_investment"])
    model.stg_cost_om               = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_specific_cost_om"])
    model.stg_maxCap                = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_maxCap"])
    model.stg_lifetime              = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_lifetime"])
    model.stg_Crate_charge          = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_Crate_charge"])
    model.stg_Crate_discharge       = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_Crate_discharge"])
    model.stg_efficiency_charge     = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_efficiency_charge"])
    model.stg_efficiency_discharge  = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_efficiency_discharge"])
    model.stg_standby_losses        = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_standby_losses"])
    model.stg_soc_initial           = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_soc_initial"])
    model.stg_soc_max               = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_soc_max"])
    model.stg_soc_min               = Param(model.Stg, within=NonNegativeReals, initialize = input_data['Storage']["storage_soc_min"])

    "Parameters of Generator"
    model.GEN_specific_cost_inv     = Param(within=NonNegativeReals, initialize = input_data['Generator']["generator_specific_cost_investment"][1])
    model.GEN_cost_om               = Param(within=NonNegativeReals, initialize = input_data['Generator']["generator_specific_cost_om"][1])
    model.GEN_capacity_max          = Param(within=NonNegativeReals, initialize = input_data['Generator']["generator_maxCap"][1]) 
    model.GEN_bigM                  = Param(within=NonNegativeReals, initialize = input_data['Generator']["generator_maxCap"][1])
    model.GEN_efficiency            = Param(within=NonNegativeReals, initialize = input_data['Generator']["generator_efficiency"][1])
    model.GEN_lifetime              = Param(within=NonNegativeReals, initialize = input_data['Generator']["generator_lifetime"][1])
    model.GEN_loading_max           = Param(within=NonNegativeReals, initialize = input_data['Generator']["generator_loading_max"][1])
    model.GEN_loading_min           = Param(within=NonNegativeReals, initialize = input_data['Generator']["generator_loading_min"][1])
    model.GEN_fuel_specific_cost    = Param(within=NonNegativeReals, initialize = input_data['Generator']["fuel_specific_cost"][1])
    model.GEN_fuel_LHV              = Param(within=NonNegativeReals, initialize = input_data['Generator']["fuel_LHV"][1])

   
    "Cost variables"
    model.total_cost        = Var(domain=NonNegativeReals)
    model.investment_cost   = Var(domain=NonNegativeReals)
    model.om_cost           = Var(domain=NonNegativeReals)
    model.fuel_cost         = Var(domain=NonNegativeReals)
    
    "Variables for bi-directional inverter"
    model.BID_capacity              = Var(domain=NonNegativeReals) # bi-directional capacity
    #model.BID_a                     = Var(model.Time, domain = Binary)
    model.rectifier_energy_output   = Var(model.Time, domain=NonNegativeReals) # energy out of BID AC -> DC (rectifier mode) at timestep t
    model.inverter_energy_output    = Var(model.Time, domain=NonNegativeReals) # energy out of BID DC -> AC (inverter mode) at timestep t

    "Variables for demand"
    model.NSL = Var(model.Time, within=NonNegativeReals)
    
    "Variables for PV"
    model.PV_capacity           = Var(domain=NonNegativeReals)
    model.PV_energy_gen_output  = Var(model.Time, domain=NonNegativeReals)

    "Variables for WT"
#    model.WT_capacity          = Var(domain=NonNegativeReals)
    model.WT_presence           = Var(model.WT, domain=Binary)
    model.WT_energy_gen_output  = Var(model.Time, model.WT, domain=NonNegativeReals)

    "Variables for Storage"
    model.stg_capacity  = Var(model.Stg, domain=NonNegativeReals)
    model.stg_presence  = Var(model.Stg, domain=Binary)
    model.stg_flowIn    = Var(model.Time, model.Stg, domain=NonNegativeReals)
    model.stg_flowOut   = Var(model.Time, model.Stg, domain=NonNegativeReals)
    model.stg_SoC       = Var(model.Time, model.Stg, domain=NonNegativeReals)
    #model.stg_a         = Var(model.Time, model.Stg, domain=Binary)

    "Variables for Generator"
    model.GEN_capacity              = Var(domain=NonNegativeReals)
    model.GEN_energy_gen_output     = Var(model.Time, domain=NonNegativeReals)
    #model.GEN_ON                    = Var(model.Time, domain=Binary)       # generator variable turning generator on = 1 an off = 0 

    "Objective"
    model.total_cost_obj           = Objective(sense=minimize,rule=total_cost_obj_rule,doc='Optimization through minimizing total cost')

    "cost constraints"
    model.om_cost_cnstr         = Constraint(rule=om_cost_rule, doc = 'Sum of all the operation and maintenance cost')
    model.investment_cost_cnstr = Constraint(rule=investment_cost_rule, doc = 'Sum of all the investment cost')
    model.fuel_cost_csntr       = Constraint(rule=fuel_cost_rule, doc = 'diesel cost over the simulated period')
    
    "Project constraints"
    model.NSL_maximum   = Constraint(rule=NSL_maximum_rule, doc = 'Non-Served Load is limited to allowed maximum')

    "Constraints for Costs"
    model.costs         = Constraint(rule = total_cost_rule, doc = 'Total cost = sum of investment + o&m costs')

    "Constraints for Power balance"
    model.AC_balance    = Constraint(model.Time, rule=AC_balance_rule, doc = 'AC power balance must be 0 at all time step')
    model.DC_balance    = Constraint(model.Time, rule=DC_balance_rule, doc = 'DC power balance must be 0 at all time step')

    "Constraint for BID"
    model.BID_inverter_capacity     = Constraint(model.Time, rule=BID_inverter_capacity_rule, doc = 'BID capacity >= inverter output at every time step')
    model.BID_rectifier_capacity    = Constraint(model.Time, rule=BID_rectifier_capacity_rule, doc = 'BID capacity >= rectifier output at every time step')
    #model.inverter_output_on       = Constraint(model.Time, rule=inverter_output_on_rule, doc = 'limits maximum capacity and makes sure that inverter and rectifier are not on at the same time')
    #model.rectifier_output_on     = Constraint(model.Time, rule=rectifier_output_on_rule, doc = 'limits maximum capacity and makes sure that inverter and rectifier are not on at the same time')

    "Constraints for PV"
    model.capacityPV    = Constraint(model.Time, rule=PV_capacity_rule, doc = 'PV energy output <= PV capacity * PV nominal ouput')
    model.capacityPVmax = Constraint(rule=PV_maximum_capacity_rule, doc = 'PV is limited to certain maximum capacity')

    "Constraints for WT"
    model.capacityWT        = Constraint(model.Time, model.WT, rule=WT_capacity_rule, doc = 'WT energy output <= WT capacity * WT nominal ouput')
    model.WT_maximum_type   = Constraint(rule = WT_maximum_type_rule, doc = 'only one WT')
#    model.capacityWTmax = Constraint(rule=WT_maximum_capacity_rule, doc = 'WT is limited to certain maximum capacity')
    
    "Constraints for Storage"
    model.stgSOC            = Constraint(model.Time, model.Stg, rule = stg_SoC_rule, doc = 'State-of-charge initialisation + dispatch')
    model.stg_maximum_SOC   = Constraint(model.Time, model.Stg, rule = stg_maximun_SoC_rule, doc = 'maximum SOC' ) 
    model.stg_minimum_SOC   = Constraint(model.Time, model.Stg, rule = stg_minimun_SoC_rule, doc = 'minimum SOC' )

    model.stg_power_charge      = Constraint(model.Time, model.Stg, rule = stg_charge_power_rule, doc = 'maximum charge power')
    model.stg_power_discharge   = Constraint(model.Time, model.Stg, rule = stg_discharge_power_rule, doc = 'maximum discharge power')
    model.capacityStgmax        = Constraint(model.Stg, rule = stg_maximum_capacity_rule, doc = 'Stg is limited to certain maximum capacity')
    model.stg_maximum_type      = Constraint(rule = stg_maximum_type_rule, doc = 'single type of battery')
    #model.stg_charge_power_on   = Constraint(model.Time, model.Stg, rule = stg_charge_power_on_rule, doc = 'make simultaneous charging and discharging impossible')
    #model.stg_discharge_power_on   = Constraint(model.Time, model.Stg, rule = stg_discharge_power_on_rule, doc = 'make simultaneous charging and discharging impossible')


    "Constraints for Generator"
    model.GEN_maximum_capacity      = Constraint(rule = GEN_maximum_capacity_rule, doc = 'Generator is limited to certain maximum capacity')
    #model.GEN_bigM_cnstr_1            = Constraint(model.Time, rule = GEN_bigM_rule_1, doc = 'bigM constraint to add on/off unit commitment')
    #model.GEN_bigM_cnstr_2            = Constraint(model.Time, rule = GEN_bigM_rule_2, doc = 'bigM constraint to add on/off unit commitment')
    model.GEN_maximum_energy_output = Constraint(model.Time, rule = GEN_maximum_energy_output_rule, doc = 'Generator capacity is based on energy output needed')
    #model.GEN_minimum_energy_output = Constraint(model.Time, rule = GEN_minimum_energy_output_rule, doc = 'Generator can only work at certain minimum load')
    #model.GEN_ON_force_off          = Constraint(model.Time, rule = GEN_ON_force_off_rule)
    
    return model





