
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Temporary function for plotting maps.
# The idea is to separate plotting methods from modules like rupture.

def plot_rupture_wire3d(rupture, ax = None):
    """
    Method for making a simple representation of a Rupture instance. 
    This method draws the outline of each quadrilateral in 3D. 

    :param rupture:
        A Rupture instance. 
    :param ax:
        A matplotlib axis (optional). 
    :returns:
        Matplotlib axis. 
    """

    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
    else:
        if 'xlim3d' not in list(ax.properties().keys()):
            raise ShakeMapException(
                'Non-3d axes object passed to plot() method.')
    for quad in rupture.getQuadrilaterals():
        x = [p.longitude for p in quad]
        x.append(x[0])
        y = [p.latitude for p in quad]
        y.append(y[0])
        z = [-p.depth for p in quad]
        z.append(z[0])
        ax.plot(x, y, z)
    return ax