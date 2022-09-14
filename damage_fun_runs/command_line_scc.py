import xarray as xr
import dscim
import yaml
from dscim.menu.simple_storage import Climate, EconVars
import pandas as pd
import numpy as np
from itertools import product
from pathlib import Path

import inquirer
from pyfiglet import Figlet
from pathlib import Path
import os
import re

master = Path(os.getcwd()) / "generated_conf.yml"
try:
    with open(master, "r") as stream:
        conf = yaml.safe_load(stream)
except FileNotFoundError:
    raise FileNotFoundError("Please run Directory_setup.py or place the config in your current working directory")

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
    
    master = Path(os.getcwd()) / "generated_conf.yml"

    with open(master, "r") as stream:
        conf = yaml.safe_load(stream)

    econ_dom = EconVars(
        path_econ=f"{conf['rffdata']['socioec_output']}/rff_USA_socioeconomics.nc4"
    )
    econ_glob = EconVars(
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
        "econ_vars": econ_dom,
        "climate_vars": Climate(**conf["rff_climate"], pulse_year=pulse_year),
        "formula": conf["sectors"][sector if not domestic else sector[:-4]]["formula"],
        "discounting_type": discount_type,
        "sector": sector,
        "ce_path": None,
        "save_path": None,
        "eta": eta,
        "rho": rho,
        "damage_function_path": Path(conf['paths']['rff_damage_function_library'])  / sector,
        "ecs_mask_path": None,
        "ecs_mask_name": None,
        "fair_dims":[],
    }

    kwargs_domestic = conf["global_parameters"].copy()
    for k, v in add_kwargs.items():
        assert (
            k not in kwargs_domestic.keys()
        ), f"{k} already set in config. Please check `global_parameters`."
        kwargs_domestic.update({k: v})

    conf["global_parameters"] = {'fair_aggregation': fair_aggregation,
     'subset_dict': {'ssp': []},
     'weitzman_parameter': weitzman_parameters,
     'save_files': []}

    add_kwargs = {
        "econ_vars": econ_glob,
        "climate_vars": Climate(**conf["rff_climate"], pulse_year=pulse_year),
        "formula": conf["sectors"][sector if not domestic else sector[:-4]]["formula"],
        "discounting_type": discount_type,
        "sector": sector,
        "ce_path": None,
        "save_path": None,
        "eta": eta,
        "rho": rho,
        "damage_function_path": Path(conf['paths']['rff_damage_function_library']) / [sector if not domestic else sector[:-4]][0], 
        "ecs_mask_path": None,
        "ecs_mask_name": None,
        "fair_dims":[],
    }

    kwargs_global = conf["global_parameters"].copy()
    for k, v in add_kwargs.items():
        assert (
            k not in kwargs_global.keys()
        ), f"{k} already set in config. Please check `global_parameters`."
        kwargs_global.update({k: v})

    menu_item_global = MENU_OPTIONS[menu_option](**kwargs_global)
    df = menu_item_global.uncollapsed_discount_factors

    if domestic:
        menu_item_domestic = MENU_OPTIONS[menu_option](**kwargs_domestic)
        md = menu_item_domestic.uncollapsed_marginal_damages
    else:
        md = menu_item_global.uncollapsed_marginal_damages

    if menu_option == "risk_aversion":
        sccs = (
            (md.rename(marginal_damages = 'scc') * df.rename(discount_factor = 'scc'))
            .sum("year")
        )     
    else:
        sccs = menu_item_global.discounted_damages(md,"constant").sum(dim="year").rename(marginal_damages = "scc")
        
    if discount_type == "euler_ramsey":
        gcnp = menu_item_global.global_consumption_no_pulse.rename('gcnp')

        # Isolate population from socioeconomics
        pop = xr.open_dataset(f"{conf['rffdata']['socioec_output']}/rff_global_socioeconomics.nc4").sel(region = 'world', drop = True).pop
       
        # Calculate global consumption no pulse per population
        a = xr.merge([pop, gcnp])  
        ypv = a.gcnp/a.pop

        # Create adjustment factor using adjustment.factor = (ypc^-eta)/mean(ypc^-eta)
        c = np.power(ypv, -eta).sel(year = pulse_year, drop = True)
        adj = (c/c.mean()).rename('adjustment_factor')

        # Merge adjustments with uncollapsed sccs
        adjustments = xr.merge([sccs,adj.to_dataset()])

        # Multiply adjustment factors and sccs, then collapse and deflate to 2020 dollars
        sccs_adjusted = (adjustments.adjustment_factor * adjustments.scc).mean(dim = 'runid') * 113.648/112.29

    return(sccs_adjusted.rename('scc'))

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
    master = Path(os.getcwd()) / "generated_conf.yml"
    with open(master, "r") as stream:
        conf = yaml.safe_load(stream)

    for j in risk_combos:
        all_arrays_uscc = []
        all_arrays_gcnp = []
        discount_type= j[1]
        menu_option = j[0]
        for i, pulse_year, sector in product(etas_rhos, pulse_years, sectors):
            print(i, pulse_year, sector) 
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

            df_scc = df_single.assign_coords(eta_rho =  str(eta) + "_" + str(rho), menu_option = menu_option, pulse_year = pulse_year, sector = re.split("_",sector)[0])
            df_scc_expanded = df_scc.expand_dims(['eta_rho','menu_option','pulse_year', 'sector'])
            if 'simulation' in df_scc_expanded.dims:
                df_scc_expanded = df_scc_expanded.drop_vars('simulation')
            all_arrays_uscc = all_arrays_uscc + [df_scc_expanded]

        df_full_scc = xr.combine_by_coords(all_arrays_uscc)
        scc_path = Path(conf['save_path']) / sector / ("full_order_uncollapsed_sccs_" + menu_option + ".nc4")
        df_full_scc.to_netcdf(scc_path)    
        print(f"SCCs are available in {str(scc_path)}")
        
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
if domestic:
    sector = [i + "_USA" for i in sector]
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


print(f"Full combined results are available in {str(Path(conf['save_path']) / sector[0])}")
