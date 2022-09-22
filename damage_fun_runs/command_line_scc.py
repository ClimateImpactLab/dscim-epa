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
import subprocess
from datetime import date


master = Path(os.getcwd()) / "generated_conf.yml"
try:
    with open(master, "r") as stream:
        conf = yaml.safe_load(stream)
except FileNotFoundError:
    raise FileNotFoundError("Please run Directory_setup.py or place the config in your current working directory")

discount_conversion_dict = {'1.016010255_9.149608e-05': '1.5% Ramsey',
                            '1.244459066_0.00197263997': '2.0% Ramsey',
                            '1.421158116_0.00461878399': '2.5% Ramsey'}   
gas_conversion_dict = {'CO2_Fossil':'CO2',
                       'N2O':'N2O',
                       'CH4':'CH4'} 
    
def makedir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        
        
def generate_meta(menu_item):
    # find machine name
    machine_name = os.getenv("HOSTNAME")
    if machine_name is None:
        try:
            machine_name = os.uname()[1]
        except AttributeError:
            machine_name = "unknown"
    
    # find git commit hash
    try:
        label = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode('ascii').strip()
    except CalledProcessError:
        label = "unknown"
    
    meta = {"Author": "Climate Impact Lab",
            "Date Created": date.today().strftime("%d/%m/%Y"),
            "Units": "2020 PPP-adjusted USD"}
    
    for attr_dict in [
        vars(menu_item),
        vars(vars(menu_item)["climate"]),
        vars(vars(menu_item)["econ_vars"]),
    ]:
        meta.update(
            {
                k: v
                for k, v in attr_dict.items()
                if (type(v) not in [xr.DataArray, xr.Dataset, pd.DataFrame])
                and k not in ["damage_function", "logger"]
            }
        )

    # update with git hash and machine name
    meta.update(dict(machine=machine_name, commit=label,url="https://github.com/ClimateImpactLab/dscim-epa/commit/"+subprocess.check_output(['git','rev-parse','HEAD']).decode('ascii').strip()))

    # convert to strs
    meta = {k: v if type(v) in [int, float] else str(v) for k, v in meta.items()}
    
    
    # exclude irrelevant attrs
    irrelevant_keys = ['econ_vars',
                       'climate',
                       'subset_dict',
                       'filename_suffix',
                       'ext_subset_start_year',
                       'ext_subset_end_year',
                       'ext_end_year',
                       'ext_method',
                       'clip_gmsl',
                       'scenario_dimensions',
                       'scc_quantiles',
                       'quantreg_quantiles',
                       'quantreg_weights',
                       'full_uncertainty_quantiles',
                       'extrap_formula',
                       'fair_dims',
                       'sector_path',
                       'save_files',
                       'save_path',
                       'delta',
                       'histclim',
                       'ce_path',
                       'gmst_path',
                       'gmsl_path']
    for k in irrelevant_keys:
        if k in meta.keys():
            del meta[k]
    
    # adjust attrs
    meta['emission_scenarios'] = 'RFF-SPv2'
    meta['damagefunc_base_period'] = meta.pop('base_period')
    meta['socioeconomics_path'] = meta.pop('path')    
    meta['gases'] = meta['gases'].split("'")
    meta['gases'] = [e for e in meta['gases'] if e not in (', ','[',']')]
    meta['gases'] = [gas_conversion_dict[gas] for gas in meta['gases']]
    
    if meta['sector']=='CAMEL_m1_c0.20':
        meta['sector'] = 'combined'
    else:
        meta['sector'] = re.split("_",meta['sector'])[0] 
        
    if domestic:
        meta.update(discounting_socioeconomics_path = f"{conf['rffdata']['socioec_output']}/rff_global_socioeconomics.nc4")
      
    return meta


# Merge attrs
def merge_meta(attrs,meta):
    if len(attrs)==0:
        attrs.update(meta)
    else:
        for meta_keys in attrs.keys():
            if str(meta[meta_keys]) not in str(attrs[meta_keys]):
                if type(attrs[meta_keys])!=list:
                    update = [attrs[meta_keys]]
                    update.append(meta[meta_keys])
                    attrs[meta_keys] = update
                else:
                    attrs[meta_keys].append(meta[meta_keys])
    return attrs
################################################################################


def epa_scghg(sector = "CAMEL_m1_c0.20",
            domestic = False,
            eta = 2.0,
            rho = 0.0,
            pulse_year = 2020,
            discount_type = "euler_ramsey",
            menu_option = "risk_aversion"):
    
    master = Path(os.getcwd()) / "generated_conf.yml"

    with open(master, "r") as stream:
        conf = yaml.safe_load(stream)

    econ_dom = EconVars(
        path_econ=f"{conf['rffdata']['socioec_output']}/rff_USA_socioeconomics.nc4"
    )
    econ_glob = EconVars(
        path_econ=f"{conf['rffdata']['socioec_output']}/rff_global_socioeconomics.nc4"
    )
    conf["global_parameters"] = {'fair_aggregation': ["uncollapsed"],
     'subset_dict': {'ssp': []},
     'weitzman_parameter': [0.5],
     'save_files': []}

    class RiskAversionRecipe(dscim.menu.risk_aversion.RiskAversionRecipe):
        @property
        def damage_function_coefficients(self) -> xr.Dataset:
            """
            Load damage function coefficients if the coefficients are provided by the user.
            Otherwise, compute them.
            """
            if self.damage_function_path is not None:
                return xr.open_dataset(
                    f"{self.damage_function_path}/{self.NAME}_{self.discounting_type}_eta{round(self.eta,3)}_rho{round(self.rho,3)}_dfc.nc4"
                )
            else:
                return self.damage_function["params"]

    MENU_OPTIONS = {
        "adding_up": dscim.menu.baseline.Baseline,
        "risk_aversion": RiskAversionRecipe,
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

    conf["global_parameters"] = {'fair_aggregation': ["uncollapsed"],
     'subset_dict': {'ssp': []},
     'weitzman_parameter': [0.5],
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
        scghgs = (
            (md.rename(marginal_damages = 'scghg') * df.rename(discount_factor = 'scghg'))
            .sum("year")* 113.648/112.29
        )     
    else:
        scghgs = menu_item_global.discounted_damages(md,"constant").sum(dim="year").rename(marginal_damages = "scghg")* 113.648/112.29
        
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

        # Merge adjustments with uncollapsed scghgs
        adjustments = xr.merge([scghgs,adj.to_dataset()])          
    
    # generate attrs           
    if domestic:
        meta = generate_meta(menu_item_domestic)
    else:
        meta = generate_meta(menu_item_global)

    return([adjustments, gcnp* 113.648/112.29, meta])


def epa_scghgs(sectors,
             domestic,
             etas_rhos,
             risk_combos = (('risk_aversion', 'euler_ramsey')),
             pulse_years = (2020,2030,2040,2050,2060,2070,2080),
             gcnp = False,
             uncollapsed = False):

            
    master = Path(os.getcwd()) / "generated_conf.yml"
    with open(master, "r") as stream:
        conf = yaml.safe_load(stream)
        
    attrs={}

    for j, pulse_year in product(risk_combos, pulse_years):
        all_arrays_uscghg = []
        all_arrays_gcnp = []
        discount_type= j[1]
        menu_option = j[0]
        for i, sector in product(etas_rhos, sectors):
            
            if sector=="CAMEL_m1_c0.20":
                sector_short = "combined"
            else:
                sector_short = re.split("_",sector)[0]
                
            eta = i[0]
            rho = i[1]

            print(f"Calculating {'domestic' if domestic else 'global'} {sector_short} scghgs {'and gcnp' if gcnp else ''} \n discount rate: {discount_conversion_dict[str(eta) + '_' + str(rho)]} \n pulse year: {pulse_year}")
            df_single_scghg, df_single_gcnp, meta = epa_scghg(sector = sector,
                                                          domestic = domestic,
                                                          discount_type = discount_type,
                                                          menu_option = menu_option,
                                                          eta = eta,
                                                          rho = rho,
                                                          pulse_year = pulse_year)

            df_scghg = df_single_scghg.assign_coords(discount_rate =  discount_conversion_dict[str(eta) + "_" + str(rho)], menu_option = menu_option, sector = sector_short)
            df_scghg_expanded = df_scghg.expand_dims(['discount_rate','menu_option', 'sector'])
            if 'simulation' in df_scghg_expanded.dims:
                df_scghg_expanded = df_scghg_expanded.drop_vars('simulation')
            all_arrays_uscghg = all_arrays_uscghg + [df_scghg_expanded]

            df_gcnp = df_single_gcnp.assign_coords(discount_rate =  discount_conversion_dict[str(eta) + "_" + str(rho)], menu_option = menu_option, sector = sector_short)
            df_gcnp_expanded = df_gcnp.expand_dims(['discount_rate','menu_option', 'sector'])
            if 'simulation' in df_gcnp_expanded.dims:
                df_gcnp_expanded = df_gcnp_expanded.drop_vars('simulation')
            all_arrays_gcnp = all_arrays_gcnp + [df_gcnp_expanded]    
        
            attrs = merge_meta(attrs,meta)
        
        print("Combining data arrays")
        df_full_scghg = xr.combine_by_coords(all_arrays_uscghg)
        df_full_gcnp = xr.combine_by_coords(all_arrays_gcnp)
        
        df_full_scghg = df_full_scghg.assign_coords(gas=[gas_conversion_dict[gas] for gas in df_full_scghg.gas.values])
        df_full_gcnp = df_full_gcnp.assign_coords(gas=[gas_conversion_dict[gas] for gas in df_full_gcnp.gas.values])
        
        gases = ['CO2','CH4', 'N2O']
        if uncollapsed:    
            for gas in gases:
                out_dir = Path(conf['save_path']) / f"{'domestic' if domestic else 'global'}_scghgs" / 'full_distributions' / gas 
                makedir(out_dir)
                uncollapsed_gas_scghgs = df_full_scghg.sel(gas = gas, drop = True).to_dataframe().reindex()
                print(f"Saving {'domestic' if domestic else 'global'} uncollapsed {sector_short} sc-{gas} \n pulse year: {pulse_year}")
                uncollapsed_gas_scghgs.to_csv(out_dir / f"sc-{gas}-dscim-{sector_short}-{pulse_year}-n10000.csv")
                attrs_save = attrs.copy()
                attrs_save['gases'] = gas
                with open(out_dir / f"attributes-{gas}-{sector_short}.txt", 'w') as f: 
                    for key, value in attrs_save.items(): 
                        f.write('%s:%s\n' % (key, value))

        df_full_scghg = (df_full_scghg.adjustment_factor * df_full_scghg.scghg).mean(dim = 'runid')

        for gas in gases:
            out_dir = Path(conf['save_path']) / f"{'domestic' if domestic else 'global'}_scghgs"   
            makedir(out_dir)
            collapsed_gas_scghg = df_full_scghg.sel(gas = gas, drop = True).rename('scghg').to_dataframe().reindex() 
            print(f"Saving {'domestic' if domestic else 'global'} collapsed {sector_short} sc-{gas} \n pulse year: {pulse_year}")
            collapsed_gas_scghg.to_csv(out_dir / f"sc-{gas}-dscim-{sector_short}-{pulse_year}.csv") 
            
        with open(out_dir / f"attributes-{sector_short}.txt", 'w') as f: 
            for key, value in attrs.items(): 
                f.write('%s:%s\n' % (key, value))
        
    if gcnp:
        out_dir = Path(conf['save_path']) / 'gcnp' 
        makedir(out_dir)
        df_full_gcnp.attrs=attrs
        print(f"Saving {sector_short} global consumption no pulse (gcnp)")
        df_full_gcnp.to_netcdf(out_dir / f"gcnp-dscim-{sector_short}.nc4")  
        print(f"gcnp is available in {str(out_dir)}")

    print(f"{'domestic' if domestic else 'global'}_scghgs are available in {str(Path(conf['save_path']))}/{'domestic' if domestic else 'global'}_scghgs")
   

        
f = Figlet(font='slant')
print(f.renderText('DSCIM'))



questions = [
    inquirer.List("sector",
        message= 'Select sector',
        choices= [
            ('Combined',"CAMEL_m1_c0.20"),
            ('Coastal','coastal_v0.20'),
            ('Agriculture','agriculture'),
            ('Mortality','mortality_v1'),
            ('Energy','energy'),
            ('Labor','labor'),
        ],
        default = ['CAMEL_m1_c0']),
    inquirer.Checkbox("eta_rhos",
        message= 'Select discount rates',
        choices= [
            (
                '1.5% Ramsey',
                [1.016010255, 9.149608e-05]
            ),
            (
                '2.0% Ramsey',
                [1.244459066, 0.00197263997]
            ),
            (
                '2.5% Ramsey',
                [1.421158116, 0.00461878399]
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
    inquirer.Checkbox("files",
        message= 'Optional files to save (will increase runtime substantially)',
        choices= [
            (
                'Global consumption no pulse',
                'gcnp'
            ),
            (
                'Uncollapsed scghgs',
                'uncollapsed'
            ),
    ])
        
]

answers = inquirer.prompt(questions)
etas_rhos = answers['eta_rhos']
sector = [answers['sector']]
pulse_years = answers['pulse_year']
domestic = answers['domestic']
gcnp = True if 'gcnp' in answers['files'] else False
uncollapsed = True if 'uncollapsed' in answers['files'] else False

if domestic:
    sector = [i + "_USA" for i in sector]

if len(etas_rhos) == 0:
    raise ValueError('You must select at least one eta, rho combination')

risk_combos = [['risk_aversion', 'euler_ramsey']] # Default
gases = ['CO2_Fossil', 'CH4', 'N2O'] # Default
epa_scghgs(sector,
         domestic,
         etas_rhos,
         risk_combos,
         pulse_years=pulse_years,
         gcnp = gcnp,
         uncollapsed = uncollapsed)


print(f"Full results are available in {str(Path(conf['save_path']))}")

