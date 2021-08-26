"Objective function"
def total_cost_obj_rule(model):
    return model.total_cost

"Total cost constraint"
def total_cost_rule(model):
    return (model.total_cost == model.investment_cost + model.om_cost*365/model.evaluated_days + model.fuel_cost*365/model.evaluated_days) # multiplication by 365/evaluated days in case evaluated days is not equal to 365

def fuel_cost_rule(model):
    return (model.fuel_cost == sum(model.GEN_energy_gen_output[t]*model.GEN_fuel_specific_cost/model.GEN_efficiency/model.GEN_fuel_LHV for t in model.Time)
                              )

def om_cost_rule(model):
    # return (model.om_cost == sum(model.PV_energy_gen_output[t]*model.pv_cost_om/8670 for t in model.Time)
    #                         +sum(sum(model.WT_energy_gen_output[t,wt]*model.WT_cost_om[wt]/8670 for t in model.Time) for wt in model.WT)
    #                         +sum((model.stg_flowOut[t]+model.stg_flowIn[t])*model.stg_cost_om/8670 for t in model.Time) 
    #                         +sum(model.inverter_energy_output[t]*model.inverter_cost_om/8670 for t in model.Time)
    #                         +sum(model.rectifier_energy_output[t]*model.inverter_cost_om/8670 for t in model.Time)
    #                         +sum(model.GEN_ON[t]*model.GEN_cost_om for t in model.Time)) # division by 8760 to get $/kWh instead of $/kW/yr
    #                         #+sum(model.GEN_ON[t] for t in model.Time)*model.GEN_cost_om) multiplication by 365/evaluated days in case evaluated period is not equal to a year
    return (model.om_cost == sum(model.PV_capacity*model.pv_nominal_output[t]*model.pv_cost_om/8670
                                +sum(model.WT_energy_gen_output[t,wt]*model.WT_cost_om[wt]/8670 for wt in model.WT) 
                                #+sum((model.stg_flowOut[t,stg]*model.stg_cost_om[stg]
                                #+model.stg_flowIn[t,stg]*model.stg_cost_om[stg])/8670 for stg in model.Stg)
                                +model.inverter_energy_output[t]*model.inverter_cost_om/8670 
                                +model.rectifier_energy_output[t]*model.inverter_cost_om/8670 #for t in model.Time))
                                +model.GEN_energy_gen_output[t]*model.GEN_cost_om/8670 for t in model.Time)
                                +sum(sum((model.stg_flowOut[t,stg] + model.stg_flowIn[t,stg]) for t in model.Time)*model.stg_cost_om[stg]/8670 for stg in model.Stg))
                                #+model.stg_flowIn[t,stg]*model.stg_cost_om[stg])/8670 for stg in model.Stg)

def investment_cost_rule(model):
    return (model.investment_cost == model.PV_capacity*model.pv_specific_cost_inv*AF(model.discount_rate, model.pv_lifetime)
                    +sum(model.WT_capacity[wt]*model.WT_presence[wt]*model.WT_specific_cost_inv[wt]*AF(model.discount_rate, model.WT_lifetime[wt]) for wt in model.WT)
                    +sum(model.stg_capacity[stg]*model.stg_specific_cost_inv[stg]*AF(model.discount_rate, model.stg_lifetime[stg]) for stg in model.Stg)
                    +model.BID_capacity*model.BID_specific_cost_inv*AF(model.discount_rate, model.BID_lifetime)
                    +model.GEN_capacity*model.GEN_specific_cost_inv*AF(model.discount_rate, model.GEN_lifetime))

def AF(r, L):
    return (r/(1-(r+1)**(-L)))

"Energy balance contraints"
# power balance AC
def AC_balance_rule(model,t):
    return(model.inverter_energy_output[t] - model.rectifier_energy_output[t]/model.rectifier_efficiency
            + sum(model.WT_energy_gen_output[t, wt] for wt in model.WT)
            + model.GEN_energy_gen_output[t]  
            == model.loads[t]-model.NSL[t])
    #return(model.inverter_energy_output[t] == model.loads[t]-model.NSL[t])

# power balance DC
def DC_balance_rule(model,t):
    return(model.PV_energy_gen_output[t] + sum((model.stg_flowOut[t,stg] - model.stg_flowIn[t,stg]) for stg in model.Stg)
            -model.inverter_energy_output[t]/model.inverter_efficiency 
            + model.rectifier_energy_output[t] 
            == 0)
    #return(model.PV_energy_output[t] - model.stg_flowIn[t] + model.stg_flowOut[t] - model.inverter_energy_output[t]/model.inverter_efficiency == 0)

"Lost load constraints"
def NSL_maximum_rule(model): # Maximum NSL allowed
    return (model.NSL_max_allowed*sum(model.loads[t] for t in model.Time) >= sum(model.NSL[t] for t in model.Time))

"Inverter constraints"
def BID_inverter_capacity_rule(model,t):
    return (model.BID_capacity >= model.inverter_energy_output[t]) 

def BID_rectifier_capacity_rule(model,t): 
    return (model.BID_capacity >= model.rectifier_energy_output[t]) 

def inverter_output_on_rule(model, t):# currently off
    return (model.inverter_energy_output[t] <= model.BID_a[t]*model.BID_max)

def rectifier_output_on_rule(model, t):# currently off
    return (model.rectifier_energy_output[t] <= (1-model.BID_a[t])*model.BID_max)

"PV constraints"
def PV_capacity_rule(model, t):
    return (model.PV_energy_gen_output[t] <= (model.PV_capacity*model.pv_nominal_output[t]))

# installed capacity must be less than maximum capacity
def PV_maximum_capacity_rule(model):
    return (model.PV_capacity <= model.pv_maxCap)

"WT constraints"
def WT_capacity_rule(model, t, wt):
    return (model.WT_energy_gen_output[t,wt] <= (model.WT_nominal_output[t,wt]*model.WT_presence[wt]))

# installed capacity must be less than maximum capacity
def WT_maximum_capacity_rule(model, wt):
    return (model.WT_capacity[wt] <= model.WT_maxCap[wt])

# limit WT to 1
def WT_maximum_type_rule(model):
    return (sum(model.WT_presence[wt] for wt in model.WT) <= 1)

"Battery constraints"
def stg_SoC_rule(model,t,stg): # State of Charge of the battery
    if t==1: # The state of charge (State_Of_Charge) for the period 1 is equal to the Battery size times the initial state of charge
        return (model.stg_SoC[t,stg] == (1-model.stg_standby_losses[stg])*model.stg_capacity[stg]*model.stg_soc_initial[stg] + model.stg_flowIn[t,stg]*model.stg_efficiency_charge[stg] - model.stg_flowOut[t,stg]/model.stg_efficiency_discharge[stg])
    else:  
        return (model.stg_SoC[t,stg] == (1-model.stg_standby_losses[stg])*model.stg_SoC[t-1,stg] + model.stg_flowIn[t,stg]*model.stg_efficiency_charge[stg] - model.stg_flowOut[t,stg]/model.stg_efficiency_discharge[stg])

def stg_maximun_SoC_rule(model,t,stg): # Maximun state of charge of the Battery
    return (model.stg_SoC[t,stg] <= model.stg_capacity[stg])

def stg_minimun_SoC_rule(model,t,stg): # Minimun state of charge
    return model.stg_SoC[t,stg] >=  model.stg_capacity[stg]*model.stg_soc_min[stg]

def stg_charge_power_rule(model,t,stg): # maximum charge power
    return model.stg_flowIn[t,stg] <= model.stg_capacity[stg]*model.stg_Crate_charge[stg]

def stg_discharge_power_rule(model,t,stg): # maximum discharge power
    return model.stg_flowOut[t,stg] <= model.stg_capacity[stg]*model.stg_Crate_discharge[stg]

def stg_maximum_capacity_rule(model,stg):
    return(model.stg_capacity[stg]  <= model.stg_maxCap[stg]*model.stg_presence[stg])

def stg_maximum_type_rule(model):
    return (sum(model.stg_presence[stg] for stg in model.Stg) <= 1)

def stg_charge_power_on_rule(model,t,stg): # currently on
    return model.stg_flowIn[t,stg] <= model.stg_a[t,stg]*model.stg_maxCap[stg]

def stg_discharge_power_on_rule(model,t,stg): # currently on
    return model.stg_flowOut[t,stg] <= (1-model.stg_a[t,stg])*model.stg_maxCap[stg]

"diesel generator constraints"

def GEN_maximum_energy_output_rule(model,t): # Maximum energy output of the diesel generator
    return model.GEN_energy_gen_output[t] <= model.GEN_capacity * model.GEN_loading_max

# minimum energy output constraint
def GEN_minimum_energy_output_rule(model,t): 
    #return model.GEN_energy_gen_output[t] >= model.GEN_capacity * model.GEN_loading_min - model.GEN_bigM*(1-model.GEN_ON[t])
    return model.GEN_energy_gen_output[t] >= model.GEN_capacity * model.GEN_loading_min

def GEN_maximum_capacity_rule(model):
    return(model.GEN_capacity  <= model.GEN_capacity_max)

def GEN_bigM_rule_1(model,t):
    return(model.GEN_energy_gen_output[t] <= model.GEN_bigM*model.GEN_ON[t])

def GEN_bigM_rule_2(model,t):
    return(model.GEN_energy_gen_output[t] >= 0.02*model.GEN_ON[t])

def GEN_ON_force_off_rule(model,t):
    return(model.GEN_ON[t] == 0)

# start-up constraint?
# number of start up constraint?
# fuel consumption curve?
        