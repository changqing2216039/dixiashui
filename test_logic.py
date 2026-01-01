import unittest
import os
import numpy as np
import db_manager
from models import groundwater_models, surfacewater_models

class TestWaterEnvApp(unittest.TestCase):
    
    def setUp(self):
        # Use a test database
        db_manager.DB_NAME = "test_water_env.db"
        db_manager.init_db()

    def tearDown(self):
        # Clean up test database
        if os.path.exists("test_water_env.db"):
            os.remove("test_water_env.db")

    def test_database_user(self):
        # Test registration
        self.assertTrue(db_manager.register_user("testuser", "password123"))
        self.assertFalse(db_manager.register_user("testuser", "password123")) # Duplicate
        
        # Test authentication
        user_id = db_manager.authenticate_user("testuser", "password123")
        self.assertIsNotNone(user_id)
        self.assertIsNone(db_manager.authenticate_user("testuser", "wrongpass"))

    def test_groundwater_instantaneous(self):
        M = 100
        A = 10
        DL = 0.5
        u = 0.1
        t = 100
        x = np.array([10.0, 20.0]) # u*t = 10, so peak should be around 10
        
        res = groundwater_models.calculate_1d_instantaneous(M, A, DL, u, t, x)
        
        # At x=10 (center of plume), concentration should be highest
        # At x=20, it should be lower
        self.assertTrue(res[0] > res[1])
        self.assertTrue(all(res >= 0))

    def test_groundwater_2d_instantaneous(self):
        M = 100
        ne = 0.3
        H = 10
        DL = 0.5
        DT = 0.1
        u = 0.1
        t = 100
        x = np.array([10.0, 20.0])
        y = np.array([0.0, 5.0]) # y=0 is center line
        
        # Calculate for single points manually or modify function to accept grid?
        # The function expects 1D arrays and returns 2D grid
        res = groundwater_models.calculate_2d_instantaneous(M, ne, H, DL, DT, u, t, x, y)
        
        # res shape is (len(y), len(x)) -> (2, 2)
        # Peak should be at x=10, y=0 (index [0, 0])
        
        c_peak = res[0, 0] # y=0, x=10
        c_off_center = res[1, 0] # y=5, x=10
        c_downstream = res[0, 1] # y=0, x=20
        
        self.assertTrue(c_peak > c_off_center) # Transverse dispersion
        self.assertTrue(c_peak > c_downstream) # Longitudinal dispersion/advection peak

    def test_groundwater_2d_continuous_numerical(self):
        # Test 2D Continuous
        C0 = 100
        Q = 1.0
        ne = 0.3
        H = 10
        DL = 0.5
        DT = 0.1
        u = 0.1
        t = 100
        x = np.array([10.0, 20.0])
        y = np.array([0.0, 5.0])
        
        res = groundwater_models.calculate_2d_continuous_numerical(
            C0, Q, ne, H, DL, DT, u, t, x, y
        )
        
        # Check shapes and non-negativity
        self.assertEqual(res.shape, (2, 2))
        self.assertTrue(np.all(res >= 0))
        
        # Should decay with distance from source (roughly, though advection moves it)
        # Centerline should be higher than edge
        self.assertTrue(res[0, 0] > res[1, 0])

    def test_groundwater_3d_instantaneous(self):
        M = 100
        ne = 0.3
        DL = 0.5
        DT = 0.1
        DV = 0.01
        u = 0.1
        t = 100
        x = np.array([10.0])
        y = np.array([0.0])
        z = np.array([0.0])
        
        res = groundwater_models.calculate_3d_instantaneous(
            M, ne, DL, DT, DV, u, t, x, y, z
        )
        self.assertTrue(res[0,0,0] > 0)

    def test_surfacewater_steady(self):
        Cp = 50
        Qp = 0.5
        Ch = 0
        Qh = 10
        K = 0.2
        u = 0.5
        x = np.array([0, 1000])
        
        res = surfacewater_models.calculate_river_1d_steady(Cp, Qp, Ch, Qh, K, u, x)
        
        # Initial concentration (mixed) should be > 0
        C0 = (Cp * Qp + Ch * Qh) / (Qp + Qh)
        self.assertAlmostEqual(res[0], C0)
        
        # Concentration should decay with distance
        self.assertTrue(res[1] < res[0])

    def test_groundwater_1d_short(self):
        # 1D Short-term Release
        C0 = 100
        DL = 0.5
        u = 0.1
        t_before = 5.0
        t_after = 20.0
        duration = 10.0
        x = np.array([5.0]) # Near u*t
        
        # Before duration ends, behaves like continuous
        c1 = groundwater_models.calculate_1d_short_release(C0, DL, u, t_before, duration, x)
        c_cont = groundwater_models.calculate_1d_continuous(C0, DL, u, t_before, x)
        self.assertAlmostEqual(c1[0], c_cont[0])
        
        # After duration ends, concentration should drop (pulse moves away)
        # Compare with continuous at same time (which would keep feeding)
        c2 = groundwater_models.calculate_1d_short_release(C0, DL, u, t_after, duration, x)
        c_cont_long = groundwater_models.calculate_1d_continuous(C0, DL, u, t_after, x)
        self.assertTrue(c2[0] < c_cont_long[0])

    def test_groundwater_2d_area_instantaneous(self):
        M = 100
        ne = 0.3
        H = 10
        DL = 0.5
        DT = 0.1
        u = 0.1
        t = 100
        x = np.array([10.0])
        y = np.array([0.0])
        width = 5.0
        length = 5.0
        
        res = groundwater_models.calculate_2d_area_instantaneous(
            M, ne, H, DL, DT, u, t, x, y, width, length
        )
        self.assertTrue(res[0,0] > 0)

if __name__ == '__main__':
    unittest.main()
