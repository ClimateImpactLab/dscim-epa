import yaml
import os
from pathlib import Path
base = os.getcwd()
inputs = Path(base) / "inputs"  
outputs = Path(base) / "outputs"  

def makedir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        
    
climate_inputs = inputs / "climate"
makedir(climate_inputs)

econ_inputs = inputs / "econ"
makedir(econ_inputs)

damage_functions = inputs / "damage_functions"
makedir(damage_functions)


conf_base = {'mortality_version': 1,
 'coastal_version': '0.20',
 'rff_climate': {'gases': ['CO2_Fossil', 'CH4', 'N2O'],
  'gmsl_path': str(climate_inputs / 'coastal_gmsl_v0.20.zarr'),
  'gmst_path': str(climate_inputs / 'GMTanom_all_temp_2001_2010_smooth.csv'),
  'gmst_fair_path': str(climate_inputs / 'ar6_rff_fair162_control_pulse_all_gases_2020-2030-2040-2050-2060-2070-2080_emis_conc_rf_temp_lambdaeff_ohc_emissions-driven_naturalfix_v5.03_Feb072022.nc'),
  'gmsl_fair_path': str(climate_inputs / 'rffar6_rff_iter0-19_fair162_control_pulse_2020-2030-2040-2050-2060-2070-2080_gmsl_emissions-driven_naturalfix_v5.03_Feb072022.zarr'),
  'damages_pulse_conversion_path': str(climate_inputs / 'conversion_v5.03_Feb072022.nc4'),
  'ecs_mask_path': None,
  'emission_scenarios': None},
 'paths': {'rff_damage_function_library': str(damage_functions)},
 'rffdata': {'socioec_output': str(econ_inputs),
  'pulse_years': [2020, 2030, 2040, 2050, 2060, 2070, 2080]},
 'sectors': {'coastal_v0.20': {'formula': 'damages ~ -1 + gmsl + np.power(gmsl, 2)'},
  'agriculture': {'formula': 'damages ~ -1 + anomaly + np.power(anomaly, 2)'},
  'mortality_v1': {'formula': 'damages ~ -1 + anomaly + np.power(anomaly, 2)'},
  'energy': {'formula': 'damages ~ -1 + anomaly + np.power(anomaly, 2)'},
  'labor': {'formula': 'damages ~ -1 + anomaly + np.power(anomaly, 2)'},
  'AMEL_m1': {'formula': 'damages ~ -1 + anomaly + np.power(anomaly, 2)'},
  'CAMEL_m1_c0.20': {'formula': 'damages ~ -1 + anomaly + np.power(anomaly, 2) + gmsl + np.power(gmsl, 2)'}}}

sectors = list(conf_base['sectors'].keys())
for i in sectors:
    makedir(outputs / i)
        
# Download inputs from internet        

with open('generated_conf.yml', 'w') as outfile:
    yaml.dump(conf_base, outfile, default_flow_style=False)
