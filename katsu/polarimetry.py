import numpy as np
from numpy import transpose
from numpy.linalg import inv
from .mueller import linear_retarder,linear_polarizer
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt

def condition_number(matrix):

    minv = np.linalg.pinv(matrix)

    # compute maximum norm https://numpy.org/doc/stable/reference/generated/numpy.linalg.norm.html
    norm = np.linalg.norm(matrix,ord=np.inf)
    ninv = np.linalg.norm(minv,ord=np.inf)

    return norm * ninv 

def full_mueller_polarimetry(thetas,power=1,return_condition_number=False,Min=None):
    """conduct a full mueller polarimeter measurement

    Parameters
    ----------
    thetas : numpy.ndarray
        np.linspace(starting_angle,ending_angle,number_of_measurements)
    power : float, optional
        power recorded on a given pixel. Defaults to 1
    return_condition_number : bool, optional
        returns condition number of the data reduction matrix. by default False
    Min : numpy.ndarray
        if provided, is the "true" Mueller matrix. This allows us to
        simulate full mueller polarimetry. by default None

    Returns
    -------
    numpy.ndarray
        Mueller matrix measured by the polarimeter
    """
    nmeas = len(thetas)

    Wmat = np.zeros([nmeas,16])
    Pmat = np.zeros([nmeas])
    th = thetas

    for i in range(nmeas):

        # Mueller Matrix of Generator using a QWR
        Mg = linear_retarder(th[i],np.pi/2) @ linear_polarizer(0)

        # Mueller Matrix of Analyzer using a QWR
        Ma = linear_polarizer(0) @ linear_retarder(th[i]*5,np.pi/2)

        ## Mueller Matrix of System and Generator
        # The Data Reduction Matrix
        Wmat[i,:] = np.kron(Ma[0,:],Mg[:,0])

        # A detector measures the first row of the analyzer matrix and first column of the generator matrix
        if Min is not None:
            Pmat[i] = (Ma[0,:] @ Min @ Mg[:,0]) * power
        else:
            Pmat[i] = power[i]

    # Compute Mueller Matrix with Moore-Penrose Pseudo Inverse
    # Calculation appears to be sensitive to the method used to compute the inverse! There's something I guess
    M = np.linalg.pinv(Wmat) @ Pmat
    M = np.reshape(M,[4,4])

    if return_condition_number == True:
        return M,condition_number(Wmat)

    else:
        return M
    
def stokes_sinusoid(theta,a0,b2,a4,b4):
    """sinusoidal response of a single rotating retarder full stokes polarimeter

    Parameters
    ----------
    theta : float
        angle of QWP
    a0 : float
        zero frequency coefficient
    b2 : float
        sin(2\theta) coefficient
    a4 : float
        cos(4\theta) coefficient
    b4 : float
        sin(4\theta) coefficient

    Returns
    -------
    numpy.ndarray
        sinusoidal response of the SRRP
    """
    return a0 + b2*np.sin(2*theta) + a4*np.cos(4*theta) + b4*np.sin(4*theta)

def full_stokes_polarimetry(thetas,Sin=None,power=None,return_coeffs=False):
    """conduct a full stokes polarimeter measurement

    Parameters
    ----------
    thetas : numpy.ndarray
        rotation angles of the QWP fast axis w.r.t. the horizontal polarizer
    Sin : numpy.ndarray, optional
        input stokes vector, used for simulating polarimetry. by default None
    power : numpy.ndarray, optional
        powers measured on detector for each angle theta, by default None
    return_coeffs : bool, optional
        option to return the stokes sinusoid coefficients. Useful for evaluating
        curve fit quality. by default None

    Returns
    -------
    _type_
        _description_
    """

    nmeas = len(thetas)
    Pmat = np.zeros([nmeas])

    # Retarder needs to rotate 2pi, break up by nmeas
    th = thetas
    thp = np.linspace(0,2*np.pi,101)

    for i in range(nmeas):

        # Mueller Matrix of analyzer
        M = linear_polarizer(0) @ linear_retarder(th[i],np.pi/2)

        # The top row is the analyzer vector
        analyzer = M[0,:]

        # Record the power
        if power is not None:
            Pmat[i] = power[i]
        else:
            Pmat[i] = np.dot(analyzer,Sin)

        # Optionally, add some photon noise


    popt,pcov = curve_fit(stokes_sinusoid,
                          th,
                          Pmat,
                          p0 = (1,1,1,1))

    a0 = popt[0]
    b2 = popt[1]
    a4 = popt[2]
    b4 = popt[3]

    # Compute the Stokes Vector
    S0 = 2*(a0 - a4)
    S1 = 4*a4
    S2 = 4*b4
    S3 = -2*b2

    if return_coeffs:
        return np.array([S0,S1,S2,S3]),popt
    else:
        return np.array([S0,S1,S2,S3])

