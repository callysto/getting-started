import numpy as np 
import matplotlib as mpl
from scipy import interpolate as it
import matplotlib.cm as cm
import scipy as sp
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import matplotlib.animation as animation
import matplotlib.pyplot as plt

def exclude_mesh(latitude, longitude, geometry, mask_excludes=False):
    '''
    Function excludes pieces of mesh which are not contained within a shape file
    
    inputs: latitude: mesh of latitude values on square grid (np.meshgrid)
            longitude:"    " longitude "       
            geometry: shapefile of the desired area
            mask_excludes: reverses the out put (now geometry is excluded, instead of just included
    
    returns: boolean mask
    '''
    # Get horizontal coords for masking purposes.
    lats = latitude
    lons = longitude
    lon2d, lat2d = np.meshgrid(lons,lats)
    # Reshape to 1D for easier iteration.
    lon2 = lon2d.reshape(-1)
    lat2 = lat2d.reshape(-1)
    mask = []
    # Iterate through all horizontal points in cube, and
    # check for containment within the specified geometry.
    for lat, lon in zip(lat2, lon2):
        this_point = gpd.geoseries.Point(lon, lat)
        res = geometry.contains(this_point)
        mask.append(res.values[0])
    mask = np.array(mask).reshape(lon2d.shape)
    if mask_excludes:
        # Invert the mask if we want to include the geometry's area.
        mask = ~mask
    return mask

def make_spline(x,y,z,interpolator, x_grid, y_grid, mask):
    
    '''
    Convenient wrapper to abstract away interpolation. 
    
    inputs: x: numpy array of x values
            y: "            " y "     "
            z: "            " z "     "
            interpolator: string of either "radial", "nearest", or "smooth" to choose interpolating
                          function.
            
            x_grid: mesh of x values over which to interpolate
            y_grid: "     " y "                               "
            mask: boolean mask of areas to exclude from the x,y mesh
    
    returns: mesh grid, inputs x,y,z after filtering, and the filtered z mesh values Z 
    '''

    # If there is a nan temperature, we can't plot it so we remove it 
    temp_mask = ~np.isnan(z)

    z = z[temp_mask]
    x = x[temp_mask]
    y = y[temp_mask]
    pos_mask = np.where(y < -70)
    z = z[pos_mask]
    x = x[pos_mask]
    y = y[pos_mask]

    B1, B2 = np.meshgrid(x_grid, y_grid, indexing='xy')
    points = np.array([x,y]).T
    values = z
    
    if interpolator == 'radial':
        spline = sp.interpolate.Rbf(x,y,z,function='cubic', smooth=5)
        Z = spline(B1.T, B2.T)
        
    if interpolator == 'nearest':
        spline = it.NearestNDInterpolator(points, values)
        Z = spline(B1.T, B2.T)
        
    if interpolator == 'smooth':
        spline = it.SmoothBivariateSpline(x,y,z)
        Z = spline.ev(B1.T, B2.T)
        
    for i in range(len(B2)):
        for j in range(len(B2)):
            if mask[i][j]:
                continue
            else:
                Z[i][j] = None
                
    return B1, B2, Z, x, y, z

def plot_instance(B1, B2, Z, x, y, z, bound, month, year,time, ax, fig, bar= False):
    
    '''
    Plots a single frame of the animation.
    
    inputs: B1: transforemd x_mesh from make_spline
            B2: transformed y_mesh "              "
            x: array of x values.
            y: "       " y      "
            z: "       " z "    "
            bound: symmetric limit of  heat color gradient
            month: month string for title
            year: year string for title
            ax: axis on which to plot
            fig: figure on which to plot
            bar (optional): whether or not to draw the color bar
            
    returns: None
    '''
    cmap = cm.get_cmap('coolwarm')

    cax = ax.pcolormesh(B2, B1, Z.T, cmap=cmap, vmin=-bound, vmax=bound)
    if bar:
        fig.colorbar(cax).set_label('Average temperature degrees c', rotation=270, size = 16)
    ax.scatter(y,x, marker ='x', s=20, label="Weather Stations\n temperature measurements\n as marked", c='black')
        

    ax.set_title(str(month) + " " + str(year) + " " + time, size = 20)
    
    for i in range(len(x)):
        ax.text(y[i], x[i], int(z[i]), color="black", fontsize=14)
    ax.legend()
    
    ax.set_xlabel("Longitude", size= 16)
    ax.set_ylabel("Latitude", size = 16)

    
def animate_map(i, monthly, anim_months, x_grid, y_grid, mask, ax, fig, daily = False, spline='nearest'):
    '''
    Creates an animation of the map heat grid. 
    
    inputs: i: frame iteration
            monthly: pandas dataframe of data
            anim_months: list of months to animate
            x_grid: mesh of x values over which to interpolate
            y_grid: "     " y "                               "
            mask: boolean mask of areas to exclude from the x,y mesh
            ax: axis on which to plot
            fig: figure to create
            spline: interpolation type
    
    returns: None
    '''
    
            
    
    to_plot = monthly[monthly['UTC'] == anim_months[i]]
    if daily:
        month = pd.to_datetime(str(anim_months[i])).strftime('%b')
        year  = pd.to_datetime(str(anim_months[i])).strftime('%d')
        time = str(pd.to_datetime(str(anim_months[i])).strftime('%r')[-2:]) + " 12 hour average"
    else: 
        month = pd.to_datetime(str(anim_months[i])).strftime('%b')
        year  = "20"+ str(pd.to_datetime(str(anim_months[i])).strftime('%y'))
        time = ''
    
    z = np.array(to_plot['Temp (°C)'])
    x = np.array(to_plot['Latitude']) 
    y = np.array(to_plot['Longitude']) 
    B1,B2,Z,x,y,z = make_spline(x, y, z, spline, x_grid, y_grid, mask)
                
    bound = max(abs(monthly['Temp (°C)'].max()), abs(monthly['Temp (°C)'].min() ))
    ax.clear()
    plot_instance(B1, B2, Z, x, y, z, bound, month, year, time, ax, fig, bar=False)
    
def reanimator(spline_type, m_list, monthly, x_grid, y_grid, mask,  ax, fig, daily=False):
    
    
    # Exit gracefully if we don't have the correct interpolation functions 
    if spline_type not in ['radial', 'smooth', 'nearest']:
        print("The interpolation only accepts arguments of either: `smooth` , `radial`, or `nearest`")
        plt.close()
        return 
    
    # Set our axis labels 
    first_month = pd.to_datetime(str(m_list[0])) 
    anim_months = m_list[1:]
    ax.set_xlabel("Longitude", size= 16)
    ax.set_ylabel("Latitude", size = 16)
    
    # Filter down to the data we want, UTC = Coordinated Universal Time
    # or the time of the data that has been changed to reflect differences in time zones. 
    
    to_plot = monthly[monthly['UTC'] == m_list[0]]
    
    # Bounds of the colorbar 
    bound = max(abs(monthly['Temp (°C)'].min()), abs(monthly['Temp (°C)'].min() ))
    
    z = np.array(to_plot['Temp (°C)'])
    x = np.array(to_plot['Latitude']) 
    y = np.array(to_plot['Longitude']) 
    
    # Here we're creating an interpolation between all the measured weather data
    B1, B2, Z, x, y, z = make_spline(x, y, z, spline_type, x_grid, y_grid, mask)
    
    # Getting month/year for plot titles 
    month = first_month.strftime('%b')
    year =  first_month.strftime('%y')
    time = first_month.strftime('%r')
    
    # Here we take our spline and data, and create a nice plot to initialize our animation 
    plot_instance(B1, B2, Z, x, y, z, bound, month, year, time, ax, fig, bar=True)
    
    # this creates our animation, using some functions from our helper functions. 
    anim = animation.FuncAnimation(fig,
                                   animate_map,
                                   interval=500, 
                                   frames=len(anim_months),
                                   fargs = (monthly, 
                                            anim_months,
                                            x_grid, 
                                            y_grid,
                                            mask, 
                                            ax, 
                                            fig, 
                                            daily,
                                            spline_type,))
    
    plt.close()
    return anim
