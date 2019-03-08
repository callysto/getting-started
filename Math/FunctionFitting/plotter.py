import numpy as np
import matplotlib.pyplot as plt

def plot_fit(func, fit_params, err_params, func_type,x,y):
    f = plt.figure(figsize = (12,8))
    ax = f.add_subplot(111)
    ax.scatter(x,y, label = "data")
    ax.plot(x, func(x, *fit_params), label = "fit")
    
    plt_string = "Best Fit Params:\n "
    for i in range(len(fit_params)):
        plt_string += str(i+1) + ": %+.3f $\pm$ %.3f ,\n " % (fit_params[i], err_params[i])
        
    plt.text(.65, 0.1,plt_string,
         horizontalalignment='left',
         verticalalignment='center',
         transform = ax.transAxes, fontsize = 16)

    ax.set_xlabel("$x$", size = 20)
    ax.set_ylabel("$f(x)$", size =20)
    ax.legend(prop={'size': 20})
    try:
        plt.title(func_type,size = 20)
    except:
        pass
    plt.show()
    