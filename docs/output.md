## Library outputs

The final product of the library is a set of net CDFs containing SCCs under different scenarios. These net CDFs can be concatenated using the `output_scc` function inside `dscim/diagnostics/fair_step.py`. The column descriptions are as follows:

#### Parameters
* `discount_type` : choice of discounting. Details of these discounting options are in `discounting_table.md`.
* `discrate` : value of constant discount rate (only applicable for `constant` and `constant_model_collapsed` discounting types, as `ramsey` and `gwr` discounting use consumption growth rates instead of a fixed value for the discount rate).
* `weitzman_parameter` : The level of consumption below which marginal utility is held constant.
* `model` : GDP growth model (`IIASA GDP` and `OECD Env-Growth`).
* `ssp`	: Population growth model (SSPs 1-5).
* `rcp` : Representative concentration pathways (`rcp45`, `rcp85`, `SSP370`).

#### SCCs
* `adding_up_median`	: The adding up menu option, with marginal damages calculated using FAIR median parameters.
* `risk_aversion_ce`	: The risk aversion menu option, with marginal damages calculated using the CE over all FAIR simulations of future global consumption with climate change.
* `risk_aversion_median`	: The risk aversion menu option, with marginal damages calculated using FAIR median parameters.
* `risk_aversion_mean`	: The risk aversion menu option, with marginal damages calculated using the mean over all FAIR simulations of future global consumption with climate change.
* `equity_ce`	: The equity menu option, with marginal damages calculated using the CE over all FAIR simulations of future global consumption with climate change.
* `equity_median`	: The equity menu option, with marginal damages calculated using FAIR median parameters.
* `equity_mean` : The equity menu option, with marginal damages calculated using the mean over all FAIR simulations of future global consumption with climate change.
