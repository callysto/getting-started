# Import libraries and modules
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dateutil import rrule
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import re
from fuzzywuzzy import fuzz 
from tqdm import tnrange
from time import sleep



# Download raw html data
def download_raw_data(province,start_year,max_pages=4):
    
    try:
        if province in {'BC','PE','NS','NL','NB','QC','ON','MB','SK','AB','YT','NT'} and type(start_year)==str and len(start_year)==4 and type(max_pages)==int:
        # Store each page in a list and parse them later
            soup_frames = []

            for i in tnrange(max_pages, desc='Downloading Data'):
                startRow = 1 + i*100
                sleep(0.01)
                base_url = "http://climate.weather.gc.ca/historical_data/search_historic_data_stations_e.html?"
                queryProvince = "searchType=stnProv&timeframe=1&lstProvince={}&optLimit=yearRange&".format(province)
                queryYear = "StartYear={}&EndYear=2018&Year=2018&Month=12&Day=10&selRowPerPage=100&txtCentralLatMin=0&txtCentralLatSec=0&txtCentralLongMin=0&txtCentralLongSec=0&".format(start_year)
                queryStartRow = "startRow={}".format(startRow)
                
                #print("URL: ", base_url + queryProvince + queryYear + queryStartRow, "\n")
                #print("row:", startRow, "\n")
                response = requests.get(base_url + queryProvince + queryYear + queryStartRow) # Using requests to read the HTML source
                soup = BeautifulSoup(response.text, 'html.parser') # Parse with Beautiful Soup
                #print(soup.prettify())
                #print(type(soup))
                soup_frames.append(soup)

            return soup_frames
        else:
            print("INVALID INPUT\n\nENTER A PROVINCE AS A STRING:\n'BC','PE','NS','NL','NB','QC','ON','MB','SK','AB','YT','NT'\nENTER YEAR AS A STRING:'1992'\nENTER A MAXIMUM NUMBER OF PAGES AS AN INTEGER, i.e. 1,2,3,4,5")
    except:
        print("INVALID INPUT\n\nENTER A PROVINCE AS A STRING:\n'BC','PE','NS','NL','NB','QC','ON','MB','SK','AB','YT','NT'\nENTER YEAR AS A STRING:'1992'\nENTER A MAXIMUM NUMBER OF PAGES AS AN INTEGER, i.e. 1,2,3,4,5")
        

        
# Convert raw html into pandas dataframe      
def generate_pandas_dataframe_from_html(soup_frames):
    
    # Empty list to store the station data
    station_data = []
    for i in tnrange(len(soup_frames), desc='Generating Pandas DataFrames'):# For each soup
        sleep(0.01)
        forms = soup_frames[i].findAll("form", {"id" : re.compile('stnRequest*')}) # We find the forms with the stnRequest* ID using regex
        #print(type(forms))
        for form in forms:
            try:

                #print(form)
                # The stationID is a child of the form
                station = form.find("input", {"name" : "StationID"})['value']
            
                # The station name is a sibling of the input element named lstProvince
                name = form.find("input", {"name" : "lstProvince"}).find_next_siblings("div")[0].text
            
                # The intervals are listed as children in a 'select' tag named timeframe
                timeframes = form.find("select", {"name" : "timeframe"}).findChildren()
                intervals =[t.text for t in timeframes]
            
                # We can find the min and max year of this station using the first and last child
                years = form.find("select", {"name" : "Year"}).findChildren()            
                min_year = years[0].text
                max_year = years[-1].text
            
                # Store the data in an array
                data = [station, name, intervals, min_year, max_year]
                station_data.append(data)
            except:
                pass

    # Create a pandas dataframe using the collected data and give it the appropriate column names
    stations_df = pd.DataFrame(station_data, columns=['StationID', 'Name', 'Intervals', 'Year Start', 'Year End'])
    return stations_df

#Select data only for specific city
def get_weather_data_by_loc(stations_df, location_name):
    
    try:
        tolerance = 90
        by_city_df = stations_df[stations_df['Name'].apply(lambda x: fuzz.token_set_ratio(x, location_name)) > tolerance]
        return by_city_df
    except:
        print("INVALID INPUT. ENTER A PANDAS DF FROM SOUPS AND A LOCATION, i.e, VANCOUVER, WHISTLER...")


# Call Environment Canada API
# Returns a dataframe of data
def getHourlyData(stationID, year, month):
    base_url = "http://climate.weather.gc.ca/climate_data/bulk_data_e.html?"
    query_url = "format=csv&stationID={}&Year={}&Month={}&timeframe=1".format(stationID, year, month)
    api_endpoint = base_url + query_url
    return pd.read_csv(api_endpoint, skiprows=15)



# Download hourly temperatures
def download_data_date_range(stationID,start_d,end_d):
    try:
        start_date = datetime.strptime(start_d, '%b%Y')
        end_date = datetime.strptime(end_d, '%b%Y')

        frames = []
        ran = [dt for dt in rrule.rrule(rrule.MONTHLY, dtstart=start_date, until=end_date)]
        ran_len = len(ran)
        for i in tnrange(ran_len, desc='Downloading Data'):    
            sleep(0.01)
            df = getHourlyData(stationID, ran[i].year, ran[i].month)
            frames.append(df)

        weather_data = pd.concat(frames)
        weather_data['Date/Time'] = pd.to_datetime(weather_data['Date/Time'])
        weather_data['Temp (°C)'] = pd.to_numeric(weather_data['Temp (°C)'])
        return weather_data
    
    except:
        print("INVALID INPUT. ENTER AN INTEGER FOR stationID, A STRING FOLLOWING THE FORMAT MonYEAR, i.e. Jun2015")
    