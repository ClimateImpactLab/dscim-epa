from dscim.menu.simple_storage import EconVars
from dscim.utils.menu_runs import run_ssps, run_rff
from dscim.utils.rff import (
    prep_rff_socioeconomics,
    aggregate_rff_weights,
    rff_damage_functions,
)
from dscim.preprocessing.preprocessing import (
    sum_AMEL,
    reduce_damages,
    subset_USA_reduced_damages,
    subset_USA_ssp_econ,
)
from dscim.preprocessing.midprocessing import (
    update_damage_function_library,
    combine_CAMEL_coefs,
)
import os, sys, yaml
from datetime import datetime

USER = os.getenv("USER")
from itertools import product
from p_tqdm import p_map
from functools import partial

import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)

###############
# PARAMETERS
###############

# choose script
master = f"/home/{USER}/repos/dscim-epa/configs/master-CAMEL_m1_c0.20.yaml"

# comment out unnecessary eta-rho combinations
eta_rhos = {
    # 2.0: 0.0,
    # 1.016010255: 9.149608e-05,
    # 1.244459066: 0.00197263997,
    1.421158116: 0.00461878399,
    # 1.567899395: 0.00770271076,
}

# domestic or global?
USA = False

# do you want to run all individual sectors or only CAMEL and its requirements?
all_sectors = False

#########################
# SET UP - do not change
#########################

# set up configs
with open(master, "r") as stream:
    conf = yaml.safe_load(stream)

for path in conf["paths"].values():
    os.makedirs(path, exist_ok=True)

# set up sectors
sectors = dict(
    AMEL=f"AMEL_m{conf['mortality_version']}",
    coastal=f"coastal_v{conf['coastal_version']}",
    CAMEL=f"CAMEL_m{conf['mortality_version']}_c{conf['coastal_version']}",
    AMEL_sectors=[
        "agriculture",
        f"mortality_v{conf['mortality_version']}",
        "energy",
        "labor",
    ],
)

if all_sectors == True:
    sectors.update(
        indiv_sectors=[sectors["AMEL"], sectors["coastal"]] + sectors["AMEL_sectors"]
    )
else:
    sectors.update(
        indiv_sectors=[
            sectors["AMEL"],
            sectors["coastal"],
            f"mortality_v{conf['mortality_version']}",
        ]
    )
sectors.update(all_sectors=[sectors["CAMEL"]])  # + sectors["indiv_sectors"])

# set a few more paths
if USA == True:
    ssp_gdp = conf["econdata"]["USA_ssp"]
    rff_gdp = f"{conf['rffdata']['socioec_output']}/rff_USA_socioeconomics.nc4"
else:
    ssp_gdp = conf["econdata"]["global_ssp"]
    rff_gdp = f"{conf['rffdata']['socioec_output']}/rff_global_socioeconomics.nc4"

# set parameters
recipes = ["adding_up", "risk_aversion"]
reductions = ["cc", "no_cc"]

####################
# SUM UP AMEL
####################

# print(f"{datetime.now()}: Summing AMEL...")

# sum_AMEL(
#     sectors=sectors["AMEL_sectors"],
#     config=master,
#     AMEL=sectors["AMEL"],
# )

###################
# REDUCE DAMAGES
###################

# for sector, reduction in product(
#     # sectors["indiv_sectors"],
#     sectors["AMEL_sectors"],
#     reductions,
# ):

#     print(f"{datetime.now()} : Reducing {sector} {reduction} adding_up ...")

#     reduce_damages(
#         sector=sector,
#         config=master,
#         recipe="adding_up",
#         reduction=reduction,
#         eta=None,
#         zero=False,
#         socioec=conf["econdata"]["global_ssp"],
#     )

#     for eta in eta_rhos.keys():

#         print(
#             f"{datetime.now()} : Reducing {sector} {reduction} risk_aversion {eta} ..."
#         )

#         reduce_damages(
#             sector=sector,
#             config=master,
#             recipe="risk_aversion",
#             reduction=reduction,
#             eta=eta,
#             zero=False,
#             socioec=conf["econdata"]["global_ssp"],
#         )

################################
# SUBSET US DAMAGES AND ECONVARS
################################

# if USA == True:

#     for sector, reduction in product(
#         # sectors["indiv_sectors"],
#         sectors["AMEL_sectors"],
#         reductions,
#     ):

#         print(f"{datetime.now()}: Subsetting US damages for {sector} {reduction}...")

#         subset_USA_reduced_damages(
#             input_path=conf["paths"]["reduced_damages_library"],
#             sector=sector,
#             reduction=reduction,
#             recipe="adding_up",
#             eta=None,
#         )

#         for eta in eta_rhos.keys():
#             subset_USA_reduced_damages(
#                 input_path=conf["paths"]["reduced_damages_library"],
#                 sector=sector,
#                 reduction=reduction,
#                 recipe="risk_aversion",
#                 eta=eta,
#             )

#     # subset_USA_ssp_econ(
#     #     in_path=conf["econdata"]["global_ssp"],
#     #     out_path=conf["econdata"]["USA_ssp"],
#     # )

#     # rename sectors according to the _USA convention
#     for k, v in sectors.items():
#         if type(v) == str:
#             sectors[k] = v + "_USA"
#         elif type(v) == list:
#             sectors[k] = [i + "_USA" for i in v]


#####################
# PREPARE RFF INPUTS
#####################

# print(f"{datetime.now()}: Preparing RFF inputs...")

# prep_rff_socioeconomics(
#     inflation_path=conf["rffdata"]["fed_inflation"],
#     rff_path=conf["rffdata"]["socioec"],
#     runid_path=conf["rffdata"]["runids"],
#     out_path=conf["rffdata"]["socioec_output"],
#     USA=USA,
# )

# aggregate_rff_weights(
#     root=conf["rffdata"]["weights_root"],
#     output=conf["rffdata"]["weights_output"],
# )

#####################
# RUN SSPs
#####################

print(f"{datetime.now()}: Generating SSP damage functions...")

run_ssps(
    sectors=sectors["indiv_sectors"],
    pulse_years=[2020],
    menu_discs=[
        ("adding_up", "constant"),
        ("risk_aversion", "euler_ramsey"),
        ("adding_up", "euler_ramsey"),
        ("risk_aversion", "constant"),
    ],
    eta_rhos=eta_rhos,
    config=master,
    AR=6,
    USA=USA,
    order="scc",
)

################################
# CREATE CAMEL DAMAGE FUNCTIONS
################################

# for eta, rho in eta_rhos.items():
#     for recipe, disc in [
#         ("adding_up", "constant"),
#         ("risk_aversion", "euler_ramsey"),
#         ("adding_up", "euler_ramsey"),
#         ("risk_aversion", "constant"),
#     ]:

#         print(
#             f"{datetime.now()}: Creating CAMEL coefficients for {recipe} {disc} {eta} {rho}..."
#         )

#         combine_CAMEL_coefs(
#             recipe=recipe,
#             disc=disc,
#             eta=eta,
#             rho=rho,
#             CAMEL=sectors["CAMEL"],
#             coastal=sectors["coastal"],
#             AMEL=sectors["AMEL"],
#             input_dir=conf["paths"]["ssp_damage_function_library"],
#             pulse_year=2020,
#         )

###############################
# RFF DAMAGE FUNCTIONS
################################

# print(f"{datetime.now()}: Creating RFF damage functions...")

# rff_damage_functions(
#     sectors=sectors["all_sectors"],
#     eta_rhos=eta_rhos,
#     USA=USA,
#     ssp_gdp=ssp_gdp,
#     rff_gdp=rff_gdp,
#     recipes_discs=[
#         ("adding_up", "constant"),
#         ("risk_aversion", "euler_ramsey"),
#         ("adding_up", "euler_ramsey"),
#         ("risk_aversion", "constant"),
#     ],
#     in_library=conf["paths"]["ssp_damage_function_library"],
#     out_library=conf["paths"]["rff_results"],
#     runid_path=conf["rffdata"]["runids"],
#     weights_path=conf["rffdata"]["weights_output"],
#     pulse_year=2020,
# )

############################
# RUN RFF
############################

print(f"{datetime.now()}: Generating RFF SCCs for 2020...")

run_rff(
    sectors=sectors["all_sectors"],
    pulse_years=[2020],
    menu_discs=[
        ("adding_up", "constant"),
        ("risk_aversion", "euler_ramsey"),
        ("adding_up", "euler_ramsey"),
        ("risk_aversion", "constant"),
    ],
    eta_rhos=eta_rhos,
    config=master,
    USA=USA,
)

print(f"{datetime.now()}: Generating RFF SCCs for later pulse years...")

run_rff(
    sectors=sectors["all_sectors"],
    pulse_years=[2030, 2040, 2050, 2060, 2070, 2080],
    menu_discs=[
        ("adding_up", "constant"),
        ("risk_aversion", "euler_ramsey"),
    ],
    eta_rhos=eta_rhos,
    config=master,
    USA=USA,
)
