
#client = MongoClient()
#database = client['okcoindb']
#collection = database['historical_data']

# Retrieve price, v_ask, and v_bid data points from the database.

import pandas as pd
import yfinance as yf
import time
from pandas_datareader import data as pdr


yf.pdr_override() 

import math  
import numpy as np
#import matplotlib.pyplot as plt
#import seaborn as sns
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
from datetime import timedelta
from tqdm import tqdm
import statistics
import numpy as np
from numpy.linalg import norm
from sklearn import linear_model
from sklearn.cluster import KMeans

import math 
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from datetime import timedelta
import statistics
from numpy.linalg import norm
from sklearn import linear_model
from sklearn.cluster import KMeans


import statsmodels.api as sm
from scipy import stats
from matplotlib import cm, pyplot as plt
from hmmlearn.hmm import GaussianHMM
import scipy
import datetime
import json
import seaborn as sns
#from sklearn.externals import joblib
import ta


#import xgboost
#from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
import os
import matplotlib.pyplot as plt
plt.rcParams["figure.figsize"] = (12,8)
from sklearn import  metrics, model_selection
#from xgboost.sklearn import XGBClassifier



ticker = [
# S AND P 500


                                                                                            'XEL'   ,
                                                                                            'YUM'   ,
                                                                                            'ABMD'  ,
                                                                                            'ADI'   ,
                                                                                            'ADM'   ,
                                                                                            'BLK'   ,
                                                                                            'CHRW'  ,
                                                                                            'DE'    ,
                                                                                            'EMN'   ,
                                                                                            'EMR'   ,
                                                                                            'GM'    ,
                                                                                            'IRM'   ,
                                                                                            'LVS'   ,
                                                                                            'MXIM'  ,
                                                                                            'PH'    ,
                                                                                            'ROST'  ,
                                                                                            'SWKS'  ,


]



# Normalized st. deviation
def std_normalized(vals):
    return np.std(vals) / np.mean(vals)

# Ratio of diff between last price and mean value to last price
def ma_ratio(vals):
    return (vals[-1] - np.mean(vals)) / vals[-1]

# z-score for volumes and price
def values_deviation(vals):
    return (vals[-1] - np.mean(vals)) / np.std(vals)



#########
def generate_timeseries(prices, n):
    """Use the first time period to generate all possible time series of length n
       and their corresponding label.

    Args:
        prices: A numpy array of floats representing prices over the first time
            period.
        n: An integer (180, 360, or 720) representing the length of time series.

    Returns:
        A 2-dimensional numpy array of size (len(prices)-n) x (n+1). Each row
        represents a time series of length n and its corresponding label
        (n+1-th column).
    """
    m = len(prices) - n
    ts = np.empty((m, n + 1))
    for i in range(m):
        ts[i, :n] = prices[i:i + n]
        ts[i, n] = prices[i + n] - prices[i + n - 1]
    return ts


def find_cluster_centers(timeseries, k):
    """Cluster timeseries in k clusters using k-means and return k cluster centers.

    Args:
        timeseries: A 2-dimensional numpy array generated by generate_timeseries().
        k: An integer representing the number of centers (e.g. 100).

    Returns:
        A 2-dimensional numpy array of size k x num_columns(timeseries). Each
        row represents a cluster center.
    """
    k_means = KMeans(n_clusters=k)
    k_means.fit(timeseries)
    return k_means.cluster_centers_

def choose_effective_centers(centers, n):
    """Choose n most effective cluster centers with high price variation."""
    return centers[np.argsort(np.ptp(centers, axis=1))[-n:]]


def predict_dpi(x, s):
    """Predict the average price change Δp_i, 1 <= i <= 3.

    Args:
        x: A numpy array of floats representing previous 180, 360, or 720 prices.
        s: A 2-dimensional numpy array generated by choose_effective_centers().

    Returns:
        A big float representing average price change Δp_i.
    """
    num = 0
    den = 0
    for i in range(len(s)):
        y_i = s[i, len(x)]
        x_i = s[i, :len(x)]
        variable = (-0.25 * norm(x -x_i)) 
        roundedvariable = round(variable, 15)
        exp = math.exp(roundedvariable)
        num += y_i * exp
        den += exp
    return num / den


def linear_regression_vars(prices, v_bid, v_ask, s1, s2, s3):
    """Use the second time period to generate the independent and dependent variables
       in the linear regression model Δp = w0 + w1 * Δp1 + w2 * Δp2 + w3 * Δp3 + w4 * r.

    Args:
        prices: A numpy array of floats representing prices over the second time
            period.
        v_bid: A numpy array of floats representing total volumes people are
            willing to buy over the second time period.
        v_ask: A numpy array of floats representing total volumes people are
            willing to sell over the second time period.
        s1: A 2-dimensional numpy array generated by choose_effective_centers()
        s2: A 2-dimensional numpy array generated by choose_effective_centers().
        s3: A 2-dimensional numpy array generated by choose_effective_centers().

    Returns:
        A tuple (X, Y) representing the independent and dependent variables in
        the linear regression model. X is a 2-dimensional numpy array and each
        row represents [Δp1, Δp2, Δp3, r]. Y is a numpy array of floats and
        each array element represents Δp.
    """
    X = np.empty((len(prices) - 721, 4))
    Y = np.empty(len(prices) - 721)
    for i in range(720, len(prices) - 1):
        dp = prices[i + 1] - prices[i]
        dp1 = predict_dpi(prices[i - 180:i], s1)
        dp2 = predict_dpi(prices[i - 360:i], s2)
        dp3 = predict_dpi(prices[i - 720:i], s3)
        r = (v_bid[i] - v_ask[i]) / (v_bid[i] + v_ask[i])
        X[i - 720, :] = [dp1, dp2, dp3, r]
        Y[i - 720] = dp
    return X, Y


def find_parameters_w(X, Y):
    """Find the parameter values w for the model which best fits X and Y.

    Args:
        X: A 2-dimensional numpy array representing the independent variables
            in the linear regression model.
        Y: A numpy array of floats representing the dependent variables in the
            linear regression model.

    Returns:
        A tuple (w0, w1, w2, w3, w4) representing the parameter values w.
    """
    clf = linear_model.LinearRegression()
    clf.fit(X, Y)
    w0 = clf.intercept_
    w1, w2, w3, w4 = clf.coef_
    return w0, w1, w2, w3, w4


def predict_dps(prices, v_bid, v_ask, s1, s2, s3, w):
    """Predict average price changes (final estimations Δp) over the third
       time period.

    Args:
        prices: A numpy array of floats representing prices over the third time
            period.
        v_bid: A numpy array of floats representing total volumes people are
            willing to buy over the third time period.
        v_ask: A numpy array of floats representing total volumes people are
            willing to sell over the third time period.
        s1: A 2-dimensional numpy array generated by choose_effective_centers()
        s2: A 2-dimensional numpy array generated by choose_effective_centers().
        s3: A 2-dimensional numpy array generated by choose_effective_centers().
        w: A tuple (w0, w1, w2, w3, w4) generated by find_parameters_w().

    Returns:
        A numpy array of floats. Each array element represents the final
        estimation Δp.
    """
    dps = []
    w0, w1, w2, w3, w4 = w
    for i in range(720, len(prices) - 1):
        dp1 = predict_dpi(prices[i - 180:i], s1)
        dp2 = predict_dpi(prices[i - 360:i], s2)
        dp3 = predict_dpi(prices[i - 720:i], s3)
        r = (v_bid[i] - v_ask[i]) / (v_bid[i] + v_ask[i])
        dp = w0 + w1 * dp1 + w2 * dp2 + w3 * dp3 + w4 * r
        dps.append(float(dp))
    return dps


def evaluate_performance(prices, dps, t, step):
    """Use the third time period to evaluate the performance of the algorithm.

    Args:
        prices: A numpy array of floats representing prices over the third time
            period.
        dps: A numpy array of floats generated by predict_dps().
        t: A number representing a threshold.
        step: An integer representing time steps (when we make trading decisions).

    Returns:
        A number representing the bank balance.
    """
    bank_balance = 0
    position = 0
    for i in range(720, len(prices) - 1, step):
        # long position - BUY
        if dps[i - 720] > t and position <= 0:
            position += 1
            bank_balance -= prices[i]
        # short position - SELL
        if dps[i - 720] < -t and position >= 0:
            position -= 1
            bank_balance += prices[i]
    # sell what you bought
    if position == 1:
        bank_balance += prices[len(prices) - 1]
    # pay back what you borrowed
    if position == -1:
        bank_balance -= prices[len(prices) - 1]
    return bank_balance







for x in ticker:
    print(x)
    #data = pdr.get_data_yahoo(x,  period = "30d",  interval = "90m")
    datayahoo =  pdr.get_data_yahoo(x, interval = "1d", start="1990-04-29", end="2020-06-15")

    datayahoo = datayahoo.reset_index()

    datayahooopen = datayahoo['Open'].values.tolist()
    datayahoohigh = datayahoo['High'].values.tolist()
    datayahoolow = datayahoo['Low'].values.tolist()
    datayahooclose = datayahoo['Close'].values.tolist()
    datayahoovolume = datayahoo['Volume'].values.tolist()

    data = pd.DataFrame(columns= ['Open', 'High', 'Low', 'Close', 'Volume'])

    data['Open'] = datayahooopen
    data['High'] = datayahoohigh
    data['Low'] = datayahoolow
    data['Close'] = datayahooclose
    data['Volume'] = datayahoovolume

    data = data.drop_duplicates()

    prices = [] # open
    v_bid = [] # high
    v_ask = [] # low
    close = [] # close
    volume = [] # volume

    prices = datayahooopen
    v_bid = datayahoohigh
    v_ask = datayahoolow
    close = datayahooclose
    volume = datayahoovolume


    num_points = len(prices)

    [prices1, prices2, prices3] = np.array_split(prices, 3)

    [v_bid1, v_bid2, v_bid3] = np.array_split(v_bid, 3)

    [v_ask1, v_ask2, v_ask3] = np.array_split(v_ask, 3)

    #  Use the first time period (prices1) to generate all possible time series of
    # appropriate length (180, 360, and 720). 
    timeseries180 = generate_timeseries(prices1, 180)
    timeseries360 = generate_timeseries(prices1, 360)
    timeseries720 = generate_timeseries(prices1, 720)


    # Cluster timeseries180 in 100 clusters using k-means, return the cluster
    # centers (centers180), and choose the 20 most effective centers (s1).
    centers180 = find_cluster_centers(timeseries180, 100)
    s1 = choose_effective_centers(centers180, 20)

    centers360 = find_cluster_centers(timeseries360, 100)
    s2 = choose_effective_centers(centers360, 20)

    centers720 = find_cluster_centers(timeseries720, 100)
    s3 = choose_effective_centers(centers720, 20)

    # Use the second time period to generate the independent and dependent
    # variables in the linear regression model:
    # Δp = w0 + w1 * Δp1 + w2 * Δp2 + w3 * Δp3 + w4 * r.

    Dpi_r, Dp = linear_regression_vars(prices2, v_bid2, v_ask2, s1, s2, s3)

    print(x)

    # Find the parameter values w (w0, w1, w2, w3, w4).
    try:
        w = find_parameters_w(Dpi_r, Dp)

        # Predict average price changes over the third time period.
        dps = predict_dps(prices3, v_bid3, v_ask3, s1, s2, s3, w)

        # What's your 'Fuck You Money' number?
        bank_balance = evaluate_performance(prices3, dps, t=0.0001, step=1)

        print(bank_balance)
    except:
        print("Weird data")