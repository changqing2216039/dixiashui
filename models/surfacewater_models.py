import numpy as np

def calculate_river_1d_steady(Cp, Qp, Ch, Qh, K, u, Ex, B, A, x_range):
    """
    1D River Steady State Mixing and Decay (HJ2.3-2018 Appendix E)
    
    Parameters:
    Cp: Pollutant concentration in discharge (mg/L)
    Qp: Discharge flow rate (m^3/s)
    Ch: Background concentration in river (mg/L)
    Qh: River flow rate (m^3/s)
    K: Decay coefficient (1/s)
    u: River velocity (m/s)
    Ex: Longitudinal dispersion coefficient (m^2/s)
    B: River width (m)
    A: Cross-sectional area (m^2)
    x_range: Array of distances (m)
    
    Returns:
    concentrations: Array of concentrations at distance x
    """
    # 1. Calculate dimensionless numbers
    # Avoid division by zero
    u = max(u, 1e-10)
    Ex = max(Ex, 1e-10)
    
    alpha = (K * Ex) / (u**2)
    Pe = (u * B) / Ex
    
    # Initialize result array
    C_res = np.zeros_like(x_range, dtype=float)
    
    # 2. Determine Case
    if alpha <= 0.027:
        if Pe >= 1:
            # Case 1: alpha <= 0.027, Pe >= 1 (Ignorable dispersion)
            # C0 = (CpQp + ChQh) / (Qp + Qh)
            C0 = (Cp * Qp + Ch * Qh) / (Qp + Qh)
            
            # C = C0 * exp(-kx/u) for x >= 0
            mask_pos = x_range >= 0
            C_res[mask_pos] = C0 * np.exp(-K * x_range[mask_pos] / u)
            # x < 0 is 0 or undefined in this simplified model? 
            # Usually for ignore dispersion model, upstream is 0 (background Ch? No, mixing equation implies Ch is mixed in C0)
            # But physically upstream should be Ch. 
            # However, the formula in image only specifies x>=0. For x<0, let's assume Ch or 0.
            # Looking at Case 2, it has formula for x<0. Case 1 implies advection dominates, so upstream diffusion is negligible.
            # So upstream C = Ch (background) or C0 (if mixed instantly at x=0). 
            # Let's set x<0 to Ch for now, or just follow formula which only defines x>=0.
            # If x_range has negative values, we need a value. 
            # Based on physics, if Pe >> 1, upstream is unaffected, so Ch.
            mask_neg = x_range < 0
            C_res[mask_neg] = Ch 
            
        else:
            # Case 2: alpha <= 0.027, Pe < 1 (Significant dispersion)
            C0 = (Cp * Qp + Ch * Qh) / (Qp + Qh)
            
            # x < 0: C = C0 * exp(ux/Ex)
            mask_neg = x_range < 0
            C_res[mask_neg] = C0 * np.exp(u * x_range[mask_neg] / Ex)
            
            # x >= 0: C = C0 * exp(-kx/u)
            mask_pos = x_range >= 0
            C_res[mask_pos] = C0 * np.exp(-K * x_range[mask_pos] / u)
            
    elif 0.027 < alpha <= 380:
        # Case 3
        # C0 modified
        sqrt_term = np.sqrt(1 + 4 * alpha)
        C0 = (Cp * Qp + Ch * Qh) / ((Qp + Qh) * sqrt_term)
        
        # x < 0
        mask_neg = x_range < 0
        term_neg = (u * x_range[mask_neg] / (2 * Ex)) * (1 + sqrt_term)
        C_res[mask_neg] = C0 * np.exp(term_neg)
        
        # x >= 0
        mask_pos = x_range >= 0
        term_pos = (u * x_range[mask_pos] / (2 * Ex)) * (1 - sqrt_term)
        C_res[mask_pos] = C0 * np.exp(term_pos)
        
    else:
        # Case 4: alpha > 380
        # C0 modified
        # C0 = (CpQp + ChQh) / (2A * sqrt(kEx)) ? Wait image says 2A*sqrt(kEx) in denominator?
        # Let's check image again. "2A\sqrt{kE_x}". Yes.
        # But wait, dimensions.
        # Numerator: Mass/Time (mg/s)
        # Denominator: m^2 * sqrt(1/s * m^2/s) = m^2 * m/s = m^3/s.
        # Result: mg/m^3 = mg/L (with unit conversion). Correct.
        
        sqrt_kEx = np.sqrt(K * Ex)
        # Note: A must be provided.
        if A <= 0: A = 1.0 # Safety
        
        # Denominator needs to match units. 
        # Cp*Qp is mg/L * m3/s = (g/m3) * m3/s = g/s. 
        # A is m2. sqrt(kEx) is m/s. Denom is m3/s.
        # Result is g/m3 = mg/L.
        
        C0 = (Cp * Qp + Ch * Qh) / (2 * A * sqrt_kEx)
        
        term_sqrt = np.sqrt(K / Ex)
        
        # x < 0
        mask_neg = x_range < 0
        C_res[mask_neg] = C0 * np.exp(x_range[mask_neg] * term_sqrt)
        
        # x >= 0
        mask_pos = x_range >= 0
        C_res[mask_pos] = C0 * np.exp(-x_range[mask_pos] * term_sqrt)

    return C_res

def calculate_river_2d_mixing(Cp, Qp, Ch, Qh, H, My, u, x_range, y_range):
    """
    2D River Mixing (Shoreline Discharge, Simplified)
    Using the image source approximation method for bounded channel.
    
    Parameters:
    Cp: Pollutant concentration in discharge
    Qp: Discharge flow rate
    Ch: River background concentration
    Qh: River flow rate
    H: River depth (m)
    My: Transverse dispersion coefficient (m^2/s)
    u: River velocity (m/s)
    x_range: Array of longitudinal distances (m)
    y_range: Array of transverse distances (m)
    
    Returns:
    grid_c: 2D array of concentrations
    """
    # Assume discharge is small compared to river width, treat as point source at bank (y=0)
    # Mass flux rate M_dot = Cp * Qp (approx)
    # C(x,y) = (M_dot / (H * sqrt(pi * My * x * u))) * exp(-u * y^2 / (4 * My * x))
    
    M_dot = Cp * Qp
    
    # Initialize grid
    X, Y = np.meshgrid(x_range, y_range)
    
    # Avoid division by zero at x=0
    X_safe = X.copy()
    X_safe[X_safe == 0] = 1e-6
    
    term1 = M_dot / (H * np.sqrt(np.pi * My * X_safe * u))
    term2 = np.exp(-(u * Y**2) / (4 * My * X_safe))
    
    # Add reflection from near bank (y=0) - already included in the basic semi-infinite solution effectively doubled?
    # Actually for bank discharge, the solution is 2 * standard Gaussian
    
    C_plume = 2 * term1 * term2
    
    # Superimpose background
    C_total = C_plume + Ch
    
    return C_total
