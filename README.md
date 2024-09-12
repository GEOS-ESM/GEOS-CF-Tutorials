# GEOS-CF Tutorials Hub

![gmao-banner](./static/img/gmao_fire_banner-1.png)

## Using this Repository

This tutorials repository relies on packages found in the available requirements.txt file. 

### Installation using pip
pip install -r requirements.txt

### Installation using Conda
conda create --name <env_name> --file requirements.txt

## CFAPI: The GEOS-CF API

CFAPI is a RESTful API that allows users to access GEOS-CF model forecasts and historical estimates.

Documentation for using the API via URL and curl requests can be found [here.](https://fluid.nccs.nasa.gov/cfapi/docs/)

This repository also contains a jupyter notebook that shows some examples for accessing and plotting a GEOS-CF forecast by requesting information from CFAPI.


## GEOS-CF on Google Earth Engine

Google Earth Engine provides a multi-petabyte catalog of satellite imagery and geospatial datasets. Selected collections from the GEOS Composition Forecast model were added to this catalog for easy availability in the GEE code editor and via the GEE Python API. 

The tutorial available in this repository explains how to access the GEOS-CF data via the GEE Python API. Users will visualize the data in time-series and in interactive maps along with data from the TROPOMI instrument. This plots and maps visualize tropospheric NO2 concentrations.

Users will also learn how to use an XGBoost model to gap-fill TROPOMI data and also predict future TROPOMI observations of tropospheric NO2.
