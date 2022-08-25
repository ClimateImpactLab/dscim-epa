import xarray as xr
import dscim
import yaml
from dscim.menu.simple_storage import Climate, EconVars, StackedDamages
import pandas as pd
import numpy as np
from xarray.testing import assert_allclose
from xarray.testing import assert_equal
from itertools import product
from pathlib import Path

import dask
import logging
import subprocess
from subprocess import CalledProcessError
from abc import ABC, abstractmethod
from dscim.descriptors import cachedproperty
from dscim.menu.decorators import save
from dscim.utils.utils import (
    model_outputs,
    compute_damages,
    c_equivalence,
    power,
    quantile_weight_quantilereg,
    extrapolate,
)
import inquirer
from pyfiglet import Figlet


# Config vs function params:
# Config should have all paths and parameters that are messy

# function params should be all of the simple parameters that catually want to be changed by EPA

def epa_scc(sector = "CAMEL_m1_c0.20",
            domestic = False,
            eta = 2.0,
            rho = 0.0,
            pulse_year = 2020,
            discount_type = "euler_ramsey",
            menu_option = "risk_aversion",
            gases = ['CO2_Fossil', 'CH4', 'N2O'],
            weitzman_parameters = [0.5],
            fair_aggregation = ["mean"]):
    
    USER = "liruixue"
    master = f"/home/{USER}/repos/dscim-epa/damage_fun_runs/master-CAMEL_m1_c0.20.yaml"
    
    with open(master, "r") as stream:
        conf = yaml.safe_load(stream)
        
    if domestic:
        econ = EconVars(
            path_econ=f"{conf['rffdata']['socioec_output']}/rff_USA_socioeconomics.nc4"
        )
    else:
        econ = EconVars(
            path_econ=f"{conf['rffdata']['socioec_output']}/rff_global_socioeconomics.nc4"
        )
    
    conf["global_parameters"] = {'fair_aggregation': fair_aggregation,
     'subset_dict': {'ssp': []},
     'weitzman_parameter': weitzman_parameters,
     'save_files': []}

    MENU_OPTIONS = {
        "adding_up": dscim.menu.baseline.Baseline,
        "risk_aversion": dscim.menu.risk_aversion.RiskAversionRecipe,
        "equity": dscim.menu.equity.EquityRecipe,
    }
    add_kwargs = {
        "econ_vars": econ,
        "climate_vars": Climate(**conf["rff_climate"], pulse_year=pulse_year),
        "formula": conf["sectors"][sector if not domestic else sector[:-4]]["formula"],
        "discounting_type": discount_type,
        "sector": sector,
        "ce_path": None,
        "save_path": None,
        "eta": eta,
        "rho": rho,
        "damage_function_path": Path(conf['paths']['rff_damage_function_library']) / sector / str(2020),
        "ecs_mask_path": None,
        "ecs_mask_name": None,
        "fair_dims":[],
    }

    kwargs = conf["global_parameters"].copy()
    for k, v in add_kwargs.items():
        assert (
            k not in kwargs.keys()
        ), f"{k} already set in config. Please check `global_parameters`."
        kwargs.update({k: v})

    menu_item = MENU_OPTIONS[menu_option](**kwargs)
    menu_item.order_plate("scc")
    uncollapsed_scc = menu_item.uncollapsed_sccs
    
    return(menu_item)
    
# This represents the full gamut of scc runs when run default
def epa_sccs(sectors =["CAMEL_m1_c0.20"],
             domestic = False,
             etas_rhos = [[1.016010255, 9.149608e-05],
               [1.244459066, 0.00197263997],
               [1.421158116, 0.00461878399]],
             risk_combos = [['risk_aversion', 'euler_ramsey']],
             pulse_years = [2020,2030,2040,2050,2060,2070,2080],
             gases = ['CO2_Fossil', 'CH4', 'N2O'],
             weitzman_parameters = [0.5],
             fair_aggregation = ["mean"]):


    for j, sector in product(risk_combos, sectors):
        all_arrays_uscc = []
        all_arrays_gcnp = []
        discount_type= j[1]
        menu_option = j[0]
        for i, pulse_year in product(etas_rhos, pulse_years):
            eta = i[0]
            rho = i[1]
            df_single = epa_scc(sector = sector,
                                domestic = domestic,
                                discount_type = discount_type,
                                menu_option = menu_option,
                                eta = eta,
                                rho = rho,
                                pulse_year = pulse_year,
                                gases = gases,
                                weitzman_parameters = weitzman_parameters,
                                fair_aggregation = fair_aggregation)

            df_scc = df_single.uncollapsed_sccs.assign_coords(eta_rhos =  str(eta) + "_" + str(rho), menu_option = menu_option, pulse_year = pulse_year)
            df_scc_expanded = df_scc.expand_dims(['eta_rhos','menu_option','pulse_year'])
            df_scc_expanded.name = "uncollapsed_sccs"
            df_scc_expanded = df_scc_expanded.to_dataset()
            all_arrays_uscc = all_arrays_uscc + [df_scc_expanded]

            df_gcnp = df_single.global_consumption_no_pulse.assign_coords(eta_rhos =  str(eta) + "_" + str(rho), menu_option = menu_option, pulse_year = pulse_year)
            df_gcnp_expanded = df_gcnp.expand_dims(['eta_rhos','menu_option','pulse_year'])
            df_gcnp_expanded.name = "global_consumption_no_pulse"
            df_gcnp_expanded = df_gcnp_expanded.to_dataset()
            all_arrays_gcnp = all_arrays_gcnp + [df_gcnp_expanded]

        df_full_scc = xr.combine_by_coords(all_arrays_uscc)
        df_full_scc.to_netcdf(Path("/home/liruixue/replication_newcode/") / sector / ("full_order_uncollapsed_sccs_" + menu_option + ".nc4"))    

        df_full_gcnp = xr.combine_by_coords(all_arrays_gcnp)
        df_full_gcnp.to_netcdf(Path("/home/liruixue/replication_newcode/") / sector / ("full_order_global_consumption_no_pulse_" + menu_option + ".nc4"))    

f = Figlet(font='slant')
print(f.renderText('DSCIM'))



questions = [
    inquirer.List("sector",
        message= 'Select sector',
        choices= [
            ('CAMEL',"CAMEL_m1_c0.20"),
            ('AMEL','AMEL_m1'),
            ('Coastal','coastal_v0.20'),
            ('Agriculture','agriculture'),
            ('Mortality','mortality_v1'),
            ('Energy','energy'),
            ('Labor','labor'),
        ],
        default = ['CAMEL_m1_c0']),
    inquirer.Checkbox("eta_rhos",
        message= 'Select [eta, rho]',
        choices= [
            (
                '(1.5% target) [1.016010255, 9.149608e-05]',
                [1.016010255, 9.149608e-05]
            ),
            (
                '(2.0% target) [1.244459066, 0.00197263997]',
                [1.244459066, 0.00197263997]
            ),
            (
                '(2.5% target) [1.421158116, 0.00461878399]',
                [1.421158116, 0.00461878399]
            ),
            (
                '(3.0% target) [1.567899395, 0.00770271076]',
                [1.567899395, 0.00770271076]
            ),
    ],
        default = [[1.016010255, 9.149608e-05],
                   [1.244459066, 0.00197263997],
                   [1.421158116, 0.00461878399]]),
    inquirer.Checkbox("pulse_year",
        message= 'Select pulse years',
        choices= [
            (
                '2020',
                2020
            ),
            (
                '2030',
                2030
            ),
            (
                '2040',
                2040
            ),
            (
                '2050',
                2050
            ),
            (
                '2060',
                2060
            ),
            (
                '2070',
                2070
            ),
            (
                '2080',
                2080
            ),

    ],
        default = [2020,2030,2040,2050,2060,2070,2080]),
    inquirer.List("domestic",
        message= 'Select valuation type',
        choices= [
            ('Global',False),
            ('Domestic',True)
        ]),
]

answers = inquirer.prompt(questions)
etas_rhos = answers['eta_rhos']
sector = [answers['sector']]
pulse_years = answers['pulse_year']
domestic = answers['domestic']
print(etas_rhos)
print(sector)
print(pulse_years)
print(domestic)
if len(etas_rhos) == 0:
    raise ValueError('You must select at least one eta, rho combination')

risk_combos = [['risk_aversion', 'euler_ramsey']] # Default
gases = ['CO2_Fossil', 'CH4', 'N2O'] # Default
weitzman_parameters = [0.5] # Default
epa_sccs(sector,
         domestic,
         etas_rhos,
         risk_combos,
         pulse_years=pulse_years)