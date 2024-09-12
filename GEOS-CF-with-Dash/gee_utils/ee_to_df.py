import datetime as dt
import pandas as pd

import ee
ee.Initialize()

class ee_subset:
    """
    A class with methods to create subsets of Earth Engine
    image collections.
      
    ...

    Attributes
    ----------
    band_dict : dict
        dictionary whose keys are band names and values are unit
        conversion values
    num_days : int
        number of days to be subset

    Methods
    -------
    get_subset_collection
        Returns a GEE collection subset for the number of days
        specified.
    get_point_df
        Takes a GEE image collection and returns a dataframe subset for the 
        number of days at a specific set of coordinates.
    """
    def __init__(self, band_dict, num_days):
        # Save band names and unit conversion values
        self.band_dict = band_dict
        self.band_list = list(band_dict.keys())
        
        # Get Dates
        # All subsets end at June 15th, 2023 for this tutorial
        f_date_datetime = dt.date.today() - dt.timedelta(5)
        f_year = f_date_datetime.year
        f_month = f_date_datetime.month
        f_day = f_date_datetime.day
        i_date_datetime = f_date_datetime - dt.timedelta(num_days)
        i_year = i_date_datetime.year
        i_month = i_date_datetime.month
        i_day = i_date_datetime.day

        # Initial date of interest (inclusive).
        self.i_date = f'{i_year}-{i_month}-{i_day}'

        # Final date of interest (exclusive).
        self.f_date = f'{f_year}-{f_month}-{f_day}'
    
    def get_subset_collection(self, collection):
        """
        Subsets a GEE collection and returns subset 
        with appropriate time-window and bands selected.
        
        Parameters
        ----------
        collection : ee.imagecollection.ImageCollection
            GEE image collection to be subset
        

        Returns
        -------
        coll_subset : ee.imagecollection.ImageCollection
            Subset of collection
        """

        # Select bands and dates for collection
        coll_subset = collection.select(self.band_list).filterDate(self.i_date, self.f_date)

        return coll_subset
        
    
    def get_point_df(self, collection, lat, lon):
        """
        Subsets a GEE collection and returns subset 
        dataframe for a specific set of coordinates.
        
        Parameters
        ----------
        collection : ee.imagecollection.ImageCollection
            GEE image collection to be subset
        lat : int
            Latitude coordinate for point of interest
        lon : int
            Longitude coordinate for point of interest
        

        Returns
        -------
        data_features: pandas.core.frame.DataFrame
            Subset of collection returned as data frame
            for selected bands, time window, and point of interest.
        """
        
        # Get subsetted collection
        coll_subset = self.get_subset_collection(collection)
        
        # EE point from lat, lon
        poi = ee.Geometry.Point(lon, lat)
        
        # Scale in meters
        scale = 1000
        
        # Get the data for the pixel intersecting the point
        data_poi = coll_subset.getRegion(poi, scale).getInfo()
        
        # Call function to turn data into dataframe
        data_features = ee_array_to_df(data_poi, self.band_list)
        
        # Convert feature units to desired units for each band
        for b in self.band_list:
            data_features[b] = data_features[b]*self.band_dict[b]

        return data_features

def ee_array_to_df(arr, list_of_bands):
    """Transforms client-side ee.Image.getRegion array to pandas.DataFrame."""
    df = pd.DataFrame(arr)

    # Rearrange the header.
    headers = df.iloc[0]
    df = pd.DataFrame(df.values[1:], columns=headers)

    # Remove rows without data inside.
    df = df[['longitude', 'latitude', 'time', *list_of_bands]].dropna()

    # Convert the data to numeric values.
    for band in list_of_bands:
        df[band] = pd.to_numeric(df[band], errors='coerce')
        
    # Convert the time field into a datetime.
    # Time values are stored differently for TROPOMI and GEOS-CF data
    # Need to remove the time columns from GEOS-CF dataframes
    if 'number' in list_of_bands[0]:
        df['datetime'] = pd.to_datetime(df['time'], unit='ms').dt.strftime('%Y-%m-%d %H:%M')
    else:
        df['datetime'] = pd.to_datetime(df['time'], unit='ms')
        # Remove time columns from GEOS-CF dataframes
        df.pop('time')

    # Keep the columns of interest.
    df = df[['datetime',  *list_of_bands]]

    df.reset_index(inplace=True)
    df.drop(columns='index', inplace=True)
    
    return df