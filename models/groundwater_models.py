import numpy as np
from scipy.special import erfc

def calculate_1d_instantaneous(M, ne, W, DL, u, t, x_range, lambda_coef=0.0):
    """
    1D Instantaneous Injection (Puff Model)
    C(x,t) = M / (2 * ne * W * sqrt(pi * DL * t)) * exp(-lambda*t - (x - ut)^2 / (4 * DL * t))
    
    Parameters:
    M: Mass of pollutant injected (g)
    ne: Effective porosity (-)
    W: Cross-sectional area of aquifer (m^2)
    DL: Longitudinal dispersion coefficient (m^2/d)
    u: Actual groundwater velocity (m/d)
    t: Time elapsed (d)
    x_range: Array of distances (m)
    lambda_coef: Reaction coefficient (1/d)
    
    Returns:
    concentrations: Array of concentrations at distance x (mg/L if M is g)
    """
    if t <= 0:
        return np.zeros_like(x_range)
    
    term1 = M / (2 * ne * W * np.sqrt(np.pi * DL * t))
    term2 = np.exp(-lambda_coef * t - ((x_range - u * t)**2) / (4 * DL * t))
    
    return term1 * term2

def calculate_2d_instantaneous_rotated(M, ne, H, DL, DT, u, t, X_grid, Y_grid, angle_deg, x_s, y_s, lambda_coef=0.0):
    """
    2D Instantaneous Injection with Rotation (Flow Direction) and Decay
    """
    if t <= 0:
        return np.zeros_like(X_grid)

    # Convert angle to radians
    theta = np.radians(angle_deg)
    
    # Translate to source relative
    dx = X_grid - x_s
    dy = Y_grid - y_s
    
    # Rotate coordinates to align with flow direction
    x_local = dx * np.cos(theta) + dy * np.sin(theta)
    y_local = -dx * np.sin(theta) + dy * np.cos(theta)
    
    # Apply standard formula using x_local (as x) and y_local (as y)
    term1 = M / (4 * np.pi * ne * H * t * np.sqrt(DL * DT))
    term2 = np.exp(-((x_local - u * t)**2) / (4 * DL * t) - (y_local**2) / (4 * DT * t))
    decay = np.exp(-lambda_coef * t)
    
    return term1 * term2 * decay

def calculate_2d_instantaneous_point_series(M, ne, H, DL, DT, u, t_array, x, y, angle_deg, x_s, y_s, lambda_coef=0.0):
    """
    Calculate concentration vs time at a specific point (x,y)
    """
    t_array = np.array(t_array)
    t_array = t_array[t_array > 0] # Avoid division by zero
    
    # Convert angle
    theta = np.radians(angle_deg)
    
    # Translate
    dx = x - x_s
    dy = y - y_s
    
    # Rotate
    x_local = dx * np.cos(theta) + dy * np.sin(theta)
    y_local = -dx * np.sin(theta) + dy * np.cos(theta)
    
    # Calculate
    term1 = M / (4 * np.pi * ne * H * t_array * np.sqrt(DL * DT))
    term2 = np.exp(-((x_local - u * t_array)**2) / (4 * DL * t_array) - (y_local**2) / (4 * DT * t_array))
    decay = np.exp(-lambda_coef * t_array)
    
    return t_array, term1 * term2 * decay

def calculate_1d_short_release(C0, DL, u, t, duration, x_range, lambda_coef=0.0):
    """
    1D Short-term Release (Superposition of Continuous Solutions)
    C(x,t) = C_cont(x, t) - C_cont(x, t - duration) * H(t - duration)
    
    Parameters:
    duration: Release duration (d)
    lambda_coef: Reaction coefficient (1/d)
    """
    c1 = calculate_1d_continuous(C0, DL, u, t, x_range, lambda_coef)
    
    if t > duration:
        c2 = calculate_1d_continuous(C0, DL, u, t - duration, x_range, lambda_coef)
        return c1 - c2
    else:
        return c1

def calculate_2d_continuous_rotated(C0, Q, ne, H, DL, DT, u, t, X_grid, Y_grid, angle_deg, x_s, y_s, lambda_coef=0.0):
    """
    2D Continuous Injection with Rotation (Numerical Integration)
    """
    num_steps = 100
    if t <= 0:
        return np.zeros_like(X_grid)
        
    taus = np.linspace(1e-5, t, num_steps)
    d_tau = taus[1] - taus[0]
    
    # Coordinate Transformation
    theta = np.radians(angle_deg)
    dx = X_grid - x_s
    dy = Y_grid - y_s
    X_local = dx * np.cos(theta) + dy * np.sin(theta)
    Y_local = -dx * np.sin(theta) + dy * np.cos(theta)
    
    C_total = np.zeros_like(X_grid)
    
    const_term = (C0 * Q) / (4 * np.pi * ne * H * np.sqrt(DL * DT))
    
    for tau in taus:
        term_exp = np.exp(-((X_local - u * tau)**2) / (4 * DL * tau) - (Y_local**2) / (4 * DT * tau))
        term_decay = np.exp(-lambda_coef * tau)
        C_step = (const_term / tau) * term_exp * term_decay
        C_total += C_step
        
    return C_total * d_tau

def calculate_2d_short_release_rotated(C0, Q, ne, H, DL, DT, u, t, duration, X_grid, Y_grid, angle_deg, x_s, y_s, lambda_coef=0.0):
    """
    2D Short-term Release with Rotation
    """
    c1 = calculate_2d_continuous_rotated(C0, Q, ne, H, DL, DT, u, t, X_grid, Y_grid, angle_deg, x_s, y_s, lambda_coef)
    
    if t > duration:
        c2 = calculate_2d_continuous_rotated(C0, Q, ne, H, DL, DT, u, t - duration, X_grid, Y_grid, angle_deg, x_s, y_s, lambda_coef)
        res = c1 - c2
        res[res < 0] = 0
        return res
    else:
        return c1

def calculate_2d_area_instantaneous_rotated(M, ne, H, DL, DT, u, t, X_grid, Y_grid, width, length, angle_deg, x_s, y_s, lambda_coef=0.0):
    """
    2D Area Source Instantaneous with Rotation
    """
    # Discretize Source Area
    nx_source = 10
    ny_source = 10
    
    xs = np.linspace(-length/2, length/2, nx_source)
    ys = np.linspace(-width/2, width/2, ny_source)
    
    M_point = M / (nx_source * ny_source)
    
    C_total = np.zeros_like(X_grid)
    
    # Coordinate Transformation
    theta = np.radians(angle_deg)
    dx = X_grid - x_s
    dy = Y_grid - y_s
    
    # Local coordinates (aligned with flow)
    X_local = dx * np.cos(theta) + dy * np.sin(theta)
    Y_local = -dx * np.sin(theta) + dy * np.cos(theta)
    
    const_term = M_point / (4 * np.pi * ne * H * t * np.sqrt(DL * DT))
    decay = np.exp(-lambda_coef * t)
    
    for x0 in xs:
        for y0 in ys:
            # Distance from source point (x0, y0) in local coords
            term_exp = np.exp(-((X_local - x0 - u * t)**2) / (4 * DL * t) - ((Y_local - y0)**2) / (4 * DT * t))
            C_total += const_term * term_exp
            
    return C_total * decay

def calculate_2d_area_continuous_rotated(C0, Q_total, ne, H, DL, DT, u, t, X_grid, Y_grid, width, length, angle_deg, x_s, y_s, lambda_coef=0.0):
    """
    2D Area Source Continuous with Rotation
    """
    nx_source = 5
    ny_source = 5
    
    xs = np.linspace(-length/2, length/2, nx_source)
    ys = np.linspace(-width/2, width/2, ny_source)
    
    Q_point = Q_total / (nx_source * ny_source)
    
    C_total = np.zeros_like(X_grid)
    
    # Coordinate Transformation
    theta = np.radians(angle_deg)
    dx = X_grid - x_s
    dy = Y_grid - y_s
    X_local = dx * np.cos(theta) + dy * np.sin(theta)
    Y_local = -dx * np.sin(theta) + dy * np.cos(theta)
    
    num_steps = 50
    taus = np.linspace(1e-5, t, num_steps)
    d_tau = taus[1] - taus[0]
    
    const_term = (C0 * Q_point) / (4 * np.pi * ne * H * np.sqrt(DL * DT))
    
    for x0 in xs:
        for y0 in ys:
            C_point = np.zeros_like(X_grid)
            for tau in taus:
                term_exp = np.exp(-((X_local - x0 - u * tau)**2) / (4 * DL * tau) - ((Y_local - y0)**2) / (4 * DT * tau))
                term_decay = np.exp(-lambda_coef * tau)
                C_point += (const_term / tau) * term_exp * term_decay
            C_total += C_point * d_tau
            
    return C_total

def calculate_3d_instantaneous(M, ne, DL, DT, DV, u, t, X_in, Y_in, Z_in, lambda_coef=0.0):
    """
    3D Instantaneous Injection
    C(x,y,z,t) = M / (8 * (pi*t)^(3/2) * ne * sqrt(DL*DT*DV)) * exp(...)
    """
    if t <= 0:
        return np.zeros_like(X_in)
        
    denom = 8 * (np.pi * t)**1.5 * ne * np.sqrt(DL * DT * DV)
    term1 = M / denom
    
    exponent = -((X_in - u * t)**2) / (4 * DL * t) - (Y_in**2) / (4 * DT * t) - (Z_in**2) / (4 * DV * t)
    decay = np.exp(-lambda_coef * t)
    
    return term1 * np.exp(exponent) * decay

def calculate_3d_continuous(C0, Q, ne, DL, DT, DV, u, t, X_in, Y_in, Z_in, lambda_coef=0.0):
    """
    3D Continuous Injection (Numerical Integration)
    """
    if t <= 0:
        return np.zeros_like(X_in)
        
    num_steps = 100
    taus = np.linspace(1e-5, t, num_steps)
    d_tau = taus[1] - taus[0]
    
    C_total = np.zeros_like(X_in)
    
    # Constant term outside integral
    const_term = (C0 * Q) / (8 * (np.pi)**1.5 * ne * np.sqrt(DL * DT * DV))
    
    for tau in taus:
        denom_tau = tau**1.5
        exponent = -((X_in - u * tau)**2) / (4 * DL * tau) - (Y_in**2) / (4 * DT * tau) - (Z_in**2) / (4 * DV * tau)
        term_decay = np.exp(-lambda_coef * tau)
        
        C_step = (const_term / denom_tau) * np.exp(exponent) * term_decay
        C_total += C_step
        
    return C_total * d_tau

def calculate_3d_short_release(C0, Q, ne, DL, DT, DV, u, t, duration, X_in, Y_in, Z_in, lambda_coef=0.0):
    """
    3D Short-term Release (Superposition)
    """
    c1 = calculate_3d_continuous(C0, Q, ne, DL, DT, DV, u, t, X_in, Y_in, Z_in, lambda_coef)
    
    if t > duration:
        c2 = calculate_3d_continuous(C0, Q, ne, DL, DT, DV, u, t - duration, X_in, Y_in, Z_in, lambda_coef)
        res = c1 - c2
        res[res < 0] = 0
        return res
    else:
        return c1

def calculate_1d_continuous(C0, DL, u, t, x_range, lambda_coef=0.0):
    """
    1D Continuous Injection
    C(x,t) = (C0 / 2) * [ exp((u-w)x/2DL)*erfc((x - wt) / (2 * sqrt(DL * t))) + exp((u+w)x/2DL) * erfc((x + wt) / (2 * sqrt(DL * t))) ]
    where w = sqrt(u^2 + 4*lambda*DL)
    
    Parameters:
    C0: Initial concentration (mg/L)
    DL: Longitudinal dispersion coefficient (m^2/d)
    u: Pore velocity (m/d)
    t: Time elapsed (d)
    x_range: Array of distances (m)
    lambda_coef: Reaction coefficient (1/d)
    
    Returns:
    concentrations: Array of concentrations at distance x
    """
    if t <= 0:
        return np.zeros_like(x_range)
    
    # Calculate w
    w = np.sqrt(u**2 + 4 * lambda_coef * DL)
    
    # Term 1
    # exp((u-w)x / 2DL) * erfc((x-wt) / 2sqrt(DL*t))
    arg1_exp = ((u - w) * x_range) / (2 * DL)
    arg1_erfc = (x_range - w * t) / (2 * np.sqrt(DL * t))
    term1 = np.exp(arg1_exp) * erfc(arg1_erfc)
    
    # Term 2
    # exp((u+w)x / 2DL) * erfc((x+wt) / 2sqrt(DL*t))
    arg2_exp = ((u + w) * x_range) / (2 * DL)
    arg2_erfc = (x_range + w * t) / (2 * np.sqrt(DL * t))
    term2 = np.exp(arg2_exp) * erfc(arg2_erfc)
    
    return (C0 / 2) * (term1 + term2)

def calculate_2d_instantaneous(M, ne, H, DL, DT, u, t, x_range, y_range):
    """
    2D Instantaneous Injection (Puff Model)
    C(x,y,t) = M / (4 * pi * ne * H * t * sqrt(DL * DT)) * exp( -((x-ut)^2)/(4*DL*t) - (y^2)/(4*DT*t) )
    
    Parameters:
    M: Mass injected (kg)
    ne: Effective porosity (-)
    H: Aquifer thickness (m)
    DL: Longitudinal dispersion coefficient (m^2/d)
    DT: Transverse dispersion coefficient (m^2/d)
    u: Pore velocity (m/d)
    t: Time elapsed (d)
    x_range: Array of x distances (m)
    y_range: Array of y distances (m)
    
    Returns:
    concentrations: 2D Array of concentrations C(x,y)
    """
    if t <= 0:
        return np.zeros((len(y_range), len(x_range)))

    X, Y = np.meshgrid(x_range, y_range)
    
    term1 = M / (4 * np.pi * ne * H * t * np.sqrt(DL * DT))
    term2 = np.exp(-((X - u * t)**2) / (4 * DL * t) - (Y**2) / (4 * DT * t))
    
    return term1 * term2
