"""
Convert chinese mapping systems to WGS84. 

Copied from https://github.com/sshuair/coord-convert/blob/master/coord_convert/transform.py 
as other dependencies except actual conversion were not needed.

Source: transform.py of https://pypi.org/project/coord-convert/
Author: sshuair
License: MIT License
"""

# pylint: skip-file
# flake8: noqa

# -*- coding: utf-8 -*-
from math import atan2, cos, fabs
from math import pi as PI
from math import sin, sqrt

# define ellipsoid
a = 6378245.0
f = 1 / 298.3
b = a * (1 - f)
ee = 1 - (b * b) / (a * a)


def outOfChina(lng, lat):
    """check weather lng and lat out of china

    Arguments:
        lng {float} -- longitude
        lat {float} -- latitude

    Returns:
        Bollen -- True or False
    """
    return not (72.004 <= lng <= 137.8347 and 0.8293 <= lat <= 55.8271)


def transformLat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * sqrt(fabs(x))
    ret = ret + (20.0 * sin(6.0 * x * PI) + 20.0 * sin(2.0 * x * PI)) * 2.0 / 3.0
    ret = ret + (20.0 * sin(y * PI) + 40.0 * sin(y / 3.0 * PI)) * 2.0 / 3.0
    ret = ret + (160.0 * sin(y / 12.0 * PI) + 320.0 * sin(y * PI / 30.0)) * 2.0 / 3.0
    return ret


def transformLon(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * sqrt(fabs(x))
    ret = ret + (20.0 * sin(6.0 * x * PI) + 20.0 * sin(2.0 * x * PI)) * 2.0 / 3.0
    ret = ret + (20.0 * sin(x * PI) + 40.0 * sin(x / 3.0 * PI)) * 2.0 / 3.0
    ret = ret + (150.0 * sin(x / 12.0 * PI) + 300.0 * sin(x * PI / 30.0)) * 2.0 / 3.0
    return ret


def wgs2gcj(wgsLon, wgsLat):
    """wgs coord to gcj

    Arguments:
        wgsLon {float} -- lon
        wgsLat {float} -- lat

    Returns:
        tuple -- gcj coords
    """

    if outOfChina(wgsLon, wgsLat):
        return wgsLon, wgsLat
    dLat = transformLat(wgsLon - 105.0, wgsLat - 35.0)
    dLon = transformLon(wgsLon - 105.0, wgsLat - 35.0)
    radLat = wgsLat / 180.0 * PI
    magic = sin(radLat)
    magic = 1 - ee * magic * magic
    sqrtMagic = sqrt(magic)
    dLat = (dLat * 180.0) / ((a * (1 - ee)) / (magic * sqrtMagic) * PI)
    dLon = (dLon * 180.0) / (a / sqrtMagic * cos(radLat) * PI)
    gcjLat = wgsLat + dLat
    gcjLon = wgsLon + dLon
    return (gcjLon, gcjLat)


def gcj2wgs(gcjLon, gcjLat):
    g0 = (gcjLon, gcjLat)
    w0 = g0
    g1 = wgs2gcj(w0[0], w0[1])
    # w1 = w0 - (g1 - g0)
    w1 = tuple(map(lambda x: x[0] - (x[1] - x[2]), zip(w0, g1, g0)))
    # delta = w1 - w0
    delta = tuple(map(lambda x: x[0] - x[1], zip(w1, w0)))
    while abs(delta[0]) >= 1e-6 or abs(delta[1]) >= 1e-6:
        w0 = w1
        g1 = wgs2gcj(w0[0], w0[1])
        # w1 = w0 - (g1 - g0)
        w1 = tuple(map(lambda x: x[0] - (x[1] - x[2]), zip(w0, g1, g0)))
        # delta = w1 - w0
        delta = tuple(map(lambda x: x[0] - x[1], zip(w1, w0)))
    return w1


def gcj2bd(gcjLon, gcjLat):
    z = sqrt(gcjLon * gcjLon + gcjLat * gcjLat) + 0.00002 * sin(gcjLat * PI * 3000.0 / 180.0)
    theta = atan2(gcjLat, gcjLon) + 0.000003 * cos(gcjLon * PI * 3000.0 / 180.0)
    bdLon = z * cos(theta) + 0.0065
    bdLat = z * sin(theta) + 0.006
    return (bdLon, bdLat)


def bd2gcj(bdLon, bdLat):
    x = bdLon - 0.0065
    y = bdLat - 0.006
    z = sqrt(x * x + y * y) - 0.00002 * sin(y * PI * 3000.0 / 180.0)
    theta = atan2(y, x) - 0.000003 * cos(x * PI * 3000.0 / 180.0)
    gcjLon = z * cos(theta)
    gcjLat = z * sin(theta)
    return (gcjLon, gcjLat)


def wgs2bd(wgsLon, wgsLat):
    gcj = wgs2gcj(wgsLon, wgsLat)
    return gcj2bd(gcj[0], gcj[1])


def bd2wgs(bdLon, bdLat):
    gcj = bd2gcj(bdLon, bdLat)
    return gcj2wgs(gcj[0], gcj[1])


class Transform:
    def transformLat(self, x, y):
        return transformLat(x, y)

    def transformLon(self, x, y):
        return transformLon(x, y)

    def wgs2gcj(self, wgsLon, wgsLat):
        return wgs2gcj(wgsLon, wgsLat)

    def gcj2wgs(self, gcjLon, gcjLat):
        return gcj2wgs(gcjLon, gcjLat)

    def gcj2bd(self, gcjLon, gcjLat):
        return gcj2bd(gcjLon, gcjLat)

    def bd2gcj(self, bdLon, bdLat):
        return bd2gcj(bdLon, bdLat)

    def wgs2bd(self, wgsLon, wgsLat):
        return wgs2bd(wgsLon, wgsLat)

    def bd2wgs(self, bdLon, bdLat):
        return bd2wgs(bdLon, bdLat)
