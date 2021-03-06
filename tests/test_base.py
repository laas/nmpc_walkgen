import os
import numpy
numpy.set_printoptions(threshold=numpy.nan, linewidth =numpy.nan)
from numpy.testing import *
import numpy.testing.decorators as decorators

from walking_generator.base import BaseGenerator as Generator
from walking_generator.base import BaseTypeFoot, BaseTypeSupportFoot

BASEDIR = os.path.dirname(os.path.abspath(__file__))

class TestBaseGenerator(TestCase):
    """
    Test if BaseGenerator is assembling everything correctly
    """
    #define tolerance for unittests
    ATOL = 1e-07
    RTOL = 1e-07

    def test_fixed_model_matrices(self):
        gen = Generator()
        secmargin = 0.04
        gen.set_security_margin(secmargin, secmargin)

        comx = [0.06591456,0.07638739,-0.1467377]
        comy = [2.49008564e-02,6.61665254e-02,6.72712187e-01]
        comz = 0.814
        footx = 0.00949035
        footy = 0.095
        footq = 0.0
        gen.set_initial_values(comx, comy, comz, footx, footy, footq)

        # NOTE usage: assert_allclose(actual, desired, rtol, atol, err_msg, verbose)

        T = gen.T
        h_com = gen.h_com
        g = gen.g

        for i in range(gen.N):
            j = i+1
            assert_allclose(gen.Pzs[i,:], (1, j*T, j**2*T**2/2 - h_com/g))
            assert_allclose(gen.Pps[i,:], (1, j*T, j**2*T**2/2))
            assert_allclose(gen.Pvs[i,:], (0,   1, j*T))
            assert_allclose(gen.Pas[i,:], (0,   0,   1))

            for j in range(gen.N):
                if j <= i:
                    assert_allclose(gen.Pzu[i,j], (3*(i-j)**2 + 3*(i-j) + 1)*T**3/6. - T*h_com/g)
                    assert_allclose(gen.Ppu[i,j], (3*(i-j)**2 + 3*(i-j) + 1)*T**3/6.)
                    assert_allclose(gen.Pvu[i,j], (2*(i-j) + 1)*T**2/2)
                    assert_allclose(gen.Pau[i,j], T)
                else:
                    assert_allclose(gen.Pzu[i,j], 0.0)
                    assert_allclose(gen.Ppu[i,j], 0.0)
                    assert_allclose(gen.Pvu[i,j], 0.0)
                    assert_allclose(gen.Pau[i,j], 0.0)

    def test_fixed_ZMP_matrices(self):
        gen = Generator()
        secmargin = 0.04
        gen.set_security_margin(secmargin, secmargin)

        comx = [0.06591456,0.07638739,-0.1467377]
        comy = [2.49008564e-02,6.61665254e-02,6.72712187e-01]
        comz = 0.814
        footx = 0.00949035
        footy = 0.095
        footq = 0.0
        gen.set_initial_values(comx, comy, comz, footx, footy, footq)

        T = gen.T
        h_com = gen.h_com
        g = gen.g

        Pzs = gen.Pps - h_com/g * gen.Pas
        Pzu = gen.Ppu - h_com/g * gen.Pau

        assert_allclose(gen.Pzs, Pzs)
        assert_allclose(gen.Pzu, Pzu)

    def test_basetypefoot_initialization(self):
        gen = Generator()
        secmargin = 0.04
        gen.set_security_margin(secmargin)

        comx = [0.06591456,0.07638739,-0.1467377]
        comy = [2.49008564e-02,6.61665254e-02,6.72712187e-01]
        comz = 0.814
        footx = 0.00949035
        footy = 0.095
        footq = 0.0
        gen.set_initial_values(comx, comy, comz, footx, footy, footq)

        currentSupport = BaseTypeSupportFoot()
        supportDeque = numpy.empty( (gen.N,) , dtype=object )
        for i in range(gen.N):
            supportDeque[i] = BaseTypeSupportFoot()

        U_kp1 =  numpy.hstack((gen.v_kp1.reshape(gen.v_kp1.size,1), gen.V_kp1))

        if (gen.currentSupport.foot == "left" ) :
            pair = "left"
            impair = "right"
        else :
            pair = "right"
            impair = "left"

        for i in range(gen.N):
            for j in range(U_kp1.shape[1]):
                if U_kp1[i][j] == 1 :
                    supportDeque[i].stepNumber = j
                    if (j % 2) == 0:
                        supportDeque[i].foot = pair
                    else :
                        supportDeque[i].foot = impair
            if i > 0 :
                supportDeque[i].ds = supportDeque[i].stepNumber -\
                                     supportDeque[i-1].stepNumber

        assert_equal(gen.currentSupport, currentSupport)
        assert_array_equal(gen.supportDeque, supportDeque)

    def test_BaseTypeFoot_update(self):
        gen = Generator()
        secmargin = 0.04
        gen.set_security_margin(secmargin, secmargin)

        comx = [0.06591456,0.07638739,-0.1467377]
        comy = [2.49008564e-02,6.61665254e-02,6.72712187e-01]
        comz = 0.814
        footx = 0.00949035
        footy = 0.095
        footq = 0.0
        gen.set_initial_values(comx, comy, comz, footx, footy, footq)

        currentSupport = BaseTypeSupportFoot(gen.f_k_x, gen.f_k_y, gen.f_k_q, "left")
        supportDeque = numpy.empty( (gen.N,) , dtype=object )
        for i in range(gen.N):
            supportDeque[i] = BaseTypeSupportFoot()

        for i in range(100):
            U_kp1 =  numpy.hstack((gen.v_kp1.reshape(gen.v_kp1.size,1), gen.V_kp1))

            if (gen.currentSupport.foot == "left" ) :
                pair = "left"
                impair = "right"
            else :
                pair = "right"
                impair = "left"

            timeLimit = gen.supportDeque[0].timeLimit

            for i in range(gen.N):
                for j in range(U_kp1.shape[1]):
                    if U_kp1[i][j] == 1 :
                        supportDeque[i].stepNumber = j
                        if (j % 2) == 0:
                            supportDeque[i].foot = pair
                        else :
                            supportDeque[i].foot = impair
                if i > 0 :
                    supportDeque[i].ds = supportDeque[i].stepNumber -\
                                         supportDeque[i-1].stepNumber
                if supportDeque[i].ds == 1 :
                    timeLimit = gen.currentTime + gen.T_step

                supportDeque[i].timeLimit = timeLimit

            assert_equal(gen.currentSupport, currentSupport)
            assert_array_equal(gen.supportDeque, supportDeque)

            assert_equal(gen.currentSupport, currentSupport)
            assert_array_equal(gen.supportDeque, supportDeque)

    def test_selection_matrix_initialization(self):
        gen = Generator(fsm_state='L/R')
        secmargin = 0.04
        gen.set_security_margin(secmargin, secmargin)

        comx = [0.06591456,0.07638739,-0.1467377]
        comy = [2.49008564e-02,6.61665254e-02,6.72712187e-01]
        comz = 0.814
        footx = 0.00949035
        footy = 0.095
        footq = 0.0
        gen.set_initial_values(comx, comy, comz, footx, footy, footq)

        nf = gen.nf
        N = gen.N
        nstep = int(gen.T_step/gen.T) # time span of single support phase

        v_kp1 = numpy.zeros(gen.v_kp1.shape)
        V_kp1 = numpy.zeros(gen.V_kp1.shape)

        v_kp1 = numpy.delete(v_kp1,0,None)
        v_kp1 = numpy.append(v_kp1,[0],axis=0)

        if v_kp1[0]==0:
            v_kp1 = numpy.zeros((N,), dtype=int)
            V_kp1 = numpy.zeros((N,nf), dtype=int)
            nf = 1
            for i in range(nstep):
                v_kp1[i] = 1
            for i in range(N-nstep):
                v_kp1[i+nstep] = 0
            step = 0
            for i in range (N) :
                step = (int)( i / nstep )
                for j in range (nf):
                    V_kp1[i,j] = (int)( i+1>nstep and j==step-1)

        else:
            V_kp1 = numpy.delete(V_kp1,0,axis=0)
            tmp = numpy.zeros( (1,V_kp1.shape[1]) , dtype=float)
            V_kp1 = numpy.append(V_kp1, tmp, axis=0)
            for j in range(V_kp1.shape[1]) :
                if V_kp1[:,j].sum() < nstep :
                    V_kp1[V_kp1.shape[0]-1][j] = 1
                    break
                else :
                    V_kp1[V_kp1.shape[0]-1][j] = 0

        assert_array_equal(gen.v_kp1, v_kp1)
        assert_array_equal(gen.V_kp1, V_kp1)

    def test_constraint_matrices_foot(self):
        # get test data
        data_A = numpy.loadtxt(os.path.join(BASEDIR, "data", "A.dat"), skiprows=1)
        data_B = numpy.loadtxt(os.path.join(BASEDIR, "data", "lbA.dat"), skiprows=1)

        # test data is arranged as follows:
        # A = (      0 ), b = (      0 ) <- first row is zero
        #     (  A_zmp )      (  B_zmp ) <- 64 ZMP constraints, i.e. 4*16
        #     ( A_foot )      ( B_foot ) <- 5 foot position constraints, i.e. nedges = 5
        #     (      0 )      (      0)  <- last rows are zero
        data_A = data_A[65:70,:]
        data_B = data_B[65:70]

        gen = Generator()
        secmargin = 0.04
        gen.set_security_margin(secmargin, secmargin)

        comx = [0.06591456,0.07638739,-0.1467377]
        comy = [2.49008564e-02,6.61665254e-02,6.72712187e-01]
        comz = 0.814
        footx = 0.00949035
        footy = 0.095
        footq = 0.0
        gen.set_initial_values(comx, comy, comz, footx, footy, footq)

        # assemble Afoot and Bfoot using our convention
        Afoot = numpy.zeros( (gen.Afoot.shape[0]-5, gen.Afoot.shape[1]-2) )
        Bfoot = numpy.zeros( gen.ubBfoot.shape[0]-5)

        # dddC_x
        a = 0; b = gen.N; c = 0; d = gen.N
        Afoot[:,a:b] = data_A[:, c:d]

        # F_x
        a = gen.N ; b = gen.N + gen.nf-1 ; c = 2*gen.N ; d = 2*gen.N + 1
        Afoot[:,a:b] = data_A[:, c:d]

        # dddC_y
        a = gen.N+gen.nf-1 ; b = 2*gen.N+gen.nf-1 ; c = gen.N ; d = 2*gen.N
        Afoot[:,a:b] = data_A[:, c:d]

        # F_y
        a = 2*gen.N+gen.nf-1 ; b = 2*(gen.N+gen.nf-1); c = 2*gen.N + 1; d = 2*gen.N + 2
        Afoot[:,a:b] = data_A[:, c:d]

        Bfoot[:] = data_B[:]

        genAfoot = numpy.zeros(data_A.shape)
        genBfoot = numpy.zeros(data_B.shape)

        # dddC_x + F_x-1
        a = gen.N + gen.nf-1
        genAfoot[:,:a] = gen.Afoot[:5,:a]

        # dddC_y + F_y-1
        a = gen.N + gen.nf-1 ; b = 2*(gen.N + gen.nf-1) ; c = gen.N + gen.nf ; d = 2*(gen.N + gen.nf)-1
        genAfoot[:,a:b] = gen.Afoot[:5,c:d]
        genAfoot = -1 * genAfoot

        genBfoot = gen.ubBfoot[:5]

#        print "Afoot:\n", Afoot
#        print "gen.Afoot:\n", genAfoot
#        print "A-B:\n", genAfoot - Afoot
#        print "A-B = 0\n", ((genAfoot - Afoot) == 0).all()
#        assert_allclose(genAfoot, Afoot, atol=self.ATOL, rtol=self.RTOL)

#        print "Bfoot:\n", Bfoot
#        print "gen.Bfoot:\n", genBfoot
#        print "A-B:\n", genBfoot - Bfoot
#        print "A-B = 0\n", ((genBfoot - Bfoot) == 0).all()
        assert_allclose(genBfoot, Bfoot, atol=self.ATOL, rtol=self.RTOL)

    def test_constraint_matrices_cop(self):
        # get test data
        data_A = numpy.loadtxt(os.path.join(BASEDIR, "data", "A.dat"), skiprows=1)
        data_B = numpy.loadtxt(os.path.join(BASEDIR, "data", "lbA.dat"), skiprows=1)

        # test data is arranged as follows:
        # A = (      0 ), b = (      0 ) <- first row is zero
        #     (  A_zmp )      (  B_zmp ) <- 64 ZMP constraints, i.e. 4*16
        #     ( A_foot )      ( B_foot ) <- 5 foot position constraints, i.e. nedges = 5
        #     (      0 )      (      0)  <- last rows are zero
        data_A = data_A[1:65,:]
        data_B = data_B[1:65]

        gen = Generator(fsm_state='L/R')
        secmargin = 0.04
        gen.set_security_margin(secmargin, secmargin)

        comx = [0.06591456,0.07638739,-0.1467377]
        comy = [2.49008564e-02,6.61665254e-02,6.72712187e-01]
        comz = 0.814
        footx = 0.00949035
        footy = 0.095
        footq = 0.0
        gen.set_initial_values(comx, comy, comz, footx, footy, footq)

        # assemble Acop and Bcop using our convention
        Acop = numpy.zeros((gen.Acop.shape[0],gen.Acop.shape[1]-2),dtype=float)
        Bcop = numpy.zeros(gen.ubBcop.shape,dtype=float)

        # dddC_x
        a = 0; b = gen.N; c = 0; d = gen.N
        Acop[:,a:b] = data_A[:, c:d]

        # F_x
        a = gen.N ; b = gen.N + gen.nf-1 ; c = 2*gen.N ; d = 2*gen.N + 1
        Acop[:,a:b] = data_A[:, c:d]

        # dddC_y
        a = gen.N+gen.nf-1 ; b = 2*gen.N+gen.nf-1 ; c = gen.N ; d = 2*gen.N
        Acop[:,a:b] = data_A[:, c:d]

        # F_y
        a = 2*gen.N+gen.nf-1 ; b = 2*(gen.N+gen.nf-1); c = 2*gen.N + 1; d = 2*gen.N + 2
        Acop[:,a:b] = data_A[:, c:d]

        Bcop = data_B[:]

        genAcop = numpy.zeros((gen.Acop.shape[0],gen.Acop.shape[1]-2))
        genBcop = numpy.zeros(gen.ubBcop.shape)

        # dddC_x + F_x-1
        a = gen.N + gen.nf-1
        genAcop[:,:a] = gen.Acop[:,:a]

        # dddC_y + F_y-1
        a = gen.N + gen.nf-1 ; b = 2*(gen.N + gen.nf-1) ; c = gen.N + gen.nf ; d = 2*(gen.N + gen.nf)-1
        genAcop[:,a:b] = gen.Acop[:,c:d]
        genAcop = -1 * genAcop
        #print "Acop:\n", Acop
        #print "\n\n genAcop:\n", genAcop
        #print "A-B:\n", genAcop - Acop
        #print "A-B = 0\n", ((genAcop - Acop) == 0).all()
        assert_allclose(genAcop, Acop, atol=self.ATOL, rtol=self.RTOL)

        print "Bcop:\n", Bcop
        print "gen.Bcop:\n", gen.ubBcop
        print "A-B:\n", gen.ubBcop - Bcop
        print "A-B = 0\n", ((gen.ubBcop - Bcop) == 0).all()
        assert_allclose(gen.ubBcop, Bcop, atol=self.ATOL, rtol=self.RTOL)

    def test_constraint_elemental_matrices_cop(self):
        gen = Generator(fsm_state='L/R')
        secmargin = 0.04
        gen.set_security_margin(secmargin, secmargin)

        comx = [0.06591456,0.07638739,-0.1467377]
        comy = [2.49008564e-02,6.61665254e-02,6.72712187e-01]
        comz = 0.814
        footx = 0.00949035
        footy = 0.095
        footq = 0.0
        gen.set_initial_values(comx, comy, comz, footx, footy, footq)

        data_V = numpy.loadtxt(os.path.join(BASEDIR, "data", "V_kp1.dat"), skiprows=0)
        assert_allclose(gen.V_kp1[:,0], data_V)

        data_Pzs = numpy.loadtxt(os.path.join(BASEDIR, "data", "Pzs.dat"), skiprows=0)
        assert_allclose(gen.Pzs, data_Pzs)

        data_VcX = numpy.loadtxt(os.path.join(BASEDIR, "data", "VcX.dat"), skiprows=0)
        assert_allclose(gen.v_kp1.dot(gen.f_k_x).round(6), data_VcX.round(6))

        data_VcY = numpy.loadtxt(os.path.join(BASEDIR, "data", "VcY.dat"), skiprows=0)
        assert_allclose(gen.v_kp1.dot(gen.f_k_y), data_VcY)
        #print gen.c_k_x
        data_comx = numpy.loadtxt(os.path.join(BASEDIR, "data", "comX.dat"), skiprows=0)
        assert_allclose(gen.c_k_x, data_comx)

        data_comy = numpy.loadtxt(os.path.join(BASEDIR, "data", "comY.dat"), skiprows=0)
        assert_allclose(gen.c_k_y, data_comy)

        repos = numpy.DataSource()

        data_DX = numpy.genfromtxt("./tests/data/DX.dat",skip_header=0)
        data_DY = numpy.genfromtxt("./tests/data/DY.dat",skip_header=0)
        data_Pzu = numpy.genfromtxt("./tests/data/Pzu.dat",skip_header=0)

        #print "data_DX:\n", data_DX
        #print "D_kp1x:\n", gen.D_kp1x
        #print "A-B:\n",((data_DX - gen.D_kp1x) == 0).all()
        assert_allclose(data_DX, gen.D_kp1x)

        #print "data_DY:\n", data_DY
        #print "D_kp1y:\n", gen.D_kp1y
        #print "A-B:\n",((data_DY - gen.D_kp1y) == 0).all()
        #print "A-B:\n",data_DY - gen.D_kp1y
        assert_allclose(data_DY, gen.D_kp1y)


        data_b_kp1 = numpy.loadtxt(os.path.join(BASEDIR, "data", "Bdxdy.dat"), skiprows=0)
        assert_allclose(gen.b_kp1, data_b_kp1)
#        print "data_Pzu:\n", data_Pzu
#        print "gen.Pzu:\n", gen.Pzu
#        print "A-B:\n",((data_Pzu - gen.Pzu) == 0).all()
        #print "A-B:\n",data_DY - gen.D_kp1y
        assert_allclose(data_Pzu,gen.Pzu)

    def test_all_zero_when_idle(self):
        gen = Generator()
        # NOTE usage: assert_allclose(actual, desired, rtol, atol, err_msg, verbose)

        gen.c_k_x[...] = 0.0
        gen.c_k_y[...] = 0.0
        gen.c_k_q[...] = 0.0

        assert_allclose(gen.c_k_x, 0.0)
        assert_allclose(gen.c_k_y, 0.0)
        assert_allclose(gen.c_k_q, 0.0)
        assert_allclose(gen.C_kp1_x, 0.0)
        assert_allclose(gen.C_kp1_y, 0.0)
        assert_allclose(gen.C_kp1_q, 0.0)
        assert_allclose(gen.dC_kp1_x, 0.0)
        assert_allclose(gen.dC_kp1_y, 0.0)
        assert_allclose(gen.dC_kp1_q, 0.0)
        assert_allclose(gen.ddC_kp1_x, 0.0)
        assert_allclose(gen.ddC_kp1_y, 0.0)
        assert_allclose(gen.ddC_kp1_q, 0.0)
        assert_allclose(gen.dddC_k_x, 0.0)
        assert_allclose(gen.dddC_k_y, 0.0)
        assert_allclose(gen.dddC_k_q, 0.0)

        gen.simulate()

        assert_allclose(gen.c_k_x, 0.0)
        assert_allclose(gen.c_k_y, 0.0)
        assert_allclose(gen.c_k_q, 0.0)
        assert_allclose(gen.C_kp1_x, 0.0)
        assert_allclose(gen.C_kp1_y, 0.0)
        assert_allclose(gen.C_kp1_q, 0.0)
        assert_allclose(gen.dC_kp1_x, 0.0)
        assert_allclose(gen.dC_kp1_y, 0.0)
        assert_allclose(gen.dC_kp1_q, 0.0)
        assert_allclose(gen.ddC_kp1_x, 0.0)
        assert_allclose(gen.ddC_kp1_y, 0.0)
        assert_allclose(gen.ddC_kp1_q, 0.0)
        assert_allclose(gen.dddC_k_x, 0.0)
        assert_allclose(gen.dddC_k_y, 0.0)
        assert_allclose(gen.dddC_k_q, 0.0)


if __name__ == '__main__':
    try:
        import nose
        nose.runmodule()
    except ImportError:
        err_str = 'nose needed for unittests.\nPlease install using:\n   sudo pip install nose'
        raise ImportError(err_str)
