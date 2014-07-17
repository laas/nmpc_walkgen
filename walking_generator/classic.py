import sys
import numpy

from base import BaseGenerator
# Try to get qpOASES SQP Problem class
try:
    from qpoases import PyOptions as Options
    from qpoases import PyPrintLevel as PrintLevel
    from qpoases import PySQProblem as SQProblem
    from qpoases import PySolutionAnalysis as SolutionAnalysis
except ImportError:
    err_str = 'Please install qpOASES python interface, else you will not be able to use this pattern generator.'
    raise ImportError(err_str)

class ClassicGenerator(BaseGenerator):
    """
    Reimplementation of current state-of-the-art pattern
    generator for HRP-2 of CNRS-LAAS, Toulouse.

    Solve QPs for position and orientation of CoM and feet
    independently of each other in each timestep.
    First solve  for orientations, then solve for the postions.
    """
    def __init__(self, N=15, T=0.1, nf=2, h_com=0.81):
        """
        Initialize pattern generator matrices through base class
        and allocate two QPs one for optimzation of orientation and
        one for position of CoM and feet.

        """
        BaseGenerator.__init__(self, N, T, nf, h_com)
        # TODO for speed up one can define members of BaseGenerator as
        #      direct views of QP data structures according to walking report
        #      Maybe do that later!

        # The pattern generator has to solve the following kind of
        # problem in each iteration

        # min_x 1/2 * x^T * H(w0) * x + x^T g(w0)
        # s.t.   lbA(w0) <= A(w0) * x <= ubA(w0)
        #         lb(w0) <=         x <= ub(wo)

        # Because of varying H and A, we have to use thr
        # SQPProblem class, which supports this kind of QPs

        # define some qpOASES specific things
        self.cpu_time = 0.0 # upper bound on CPU time
        self.nwsr = 1000    # # of working set recalculations
        self.options = Options()
        self.options.setToMPC()
        #self.options.printLevel = PrintLevel.LOW

        # FOR ORIENTATIONS
        # define dimensions
        self.ori_nv = self.N + self.nf
        self.ori_nc = 1

        # setup problem
        self.ori_dofs = numpy.zeros(self.ori_nv)

        self.ori_qp = SQProblem(self.ori_nv, self.ori_nc)
        #self.ori_qp.setOptions(self.options)

        self.ori_H   = numpy.zeros((self.ori_nv,self.ori_nv))
        self.ori_A   = numpy.zeros((self.ori_nc,self.ori_nv))
        self.ori_g   = numpy.zeros((self.ori_nv,))
        self.ori_lb  = -numpy.ones((self.ori_nv,))*1e+08
        self.ori_ub  =  numpy.ones((self.ori_nv,))*1e+08
        self.ori_lbA = -numpy.ones((self.ori_nc,))*1e+08
        self.ori_ubA =  numpy.ones((self.ori_nc,))*1e+08

        self._ori_qp_is_initialized = False

        # FOR POSITIONS
        # define dimensions
        self.pos_nv = 2*(self.N + self.nf)
        self.pos_nc = 1

        # setup problem
        self.pos_dofs = numpy.zeros(self.pos_nv)

        self.pos_qp = SQProblem(self.pos_nv, self.pos_nc)
        #self.pos_qp.setOptions(self.options)

        self.pos_H   = numpy.zeros((self.pos_nv,self.pos_nv))
        self.pos_A   = numpy.zeros((self.pos_nc,self.pos_nv))
        self.pos_g   = numpy.zeros((self.pos_nv,))
        self.pos_lb  = -numpy.ones((self.pos_nv,))*1e+08
        self.pos_ub  =  numpy.ones((self.pos_nv,))*1e+08
        self.pos_lbA = -numpy.ones((self.pos_nc,))*1e+08
        self.pos_ubA =  numpy.ones((self.pos_nc,))*1e+08

        self._pos_qp_is_initialized = False

        # setup analyzer for solution analysis
        analyser = SolutionAnalysis()

        # setup other stuff
        self._Q = numpy.zeros((self.N + self.nf, self.N + self.nf))
        self._p = numpy.zeros((self.N + self.nf,))

    def solve(self):
        """ Process and solve problem, s.t. pattern generator data is consistent """
        self._preprocess_solution()
        self._solve_qp()
        self._postprocess_solution()

    def _preprocess_solution(self):
        """ Update matrices and get them into the QP data structures """
        # rename for convenience
        N  = self.N
        nf = self.nf

        # ORIENTATIONS

        # initialize with actual values, else take last known solution
        # NOTE for warmstart last solution is taken from qpOASES internal memory
        if not self._ori_qp_is_initialized:
            # ori_dofs = ( dddC_kp1_q )
            #            (      F_k_q )

            self.ori_dofs[:N]   = self.dddC_k_q
            self.ori_dofs[-nf:] = self.F_k_q

            # TODO guess initial active set

        # define QP matrices
        #self.ori_H  [...] = 0.0
        #self.ori_A  [...] = 0.0
        #self.ori_g  [...] = 0.0
        #self.ori_lb [...] = 0.0
        #self.ori_ub [...] = 0.0
        #self.ori_lbA[...] = 0.0
        #self.ori_ubA[...] = 0.0

        # POSITIONS

        # initialize with actual values, else take last known solution
        # NOTE for warmstart last solution is taken from qpOASES internal memory
        if not self._pos_qp_is_initialized:
            # pos_dofs = ( dddC_kp1_x )
            #            (      F_k_x )
            #            ( dddC_kp1_y )
            #            (      F_k_y )

            self.pos_dofs[0  :0+N   ] = self.dddC_k_x
            self.pos_dofs[0+N:0+N+nf] = self.F_k_x
            a = N+nf
            self.pos_dofs[a  :a+N   ] = self.dddC_k_y
            self.pos_dofs[a+N:a+N+nf] = self.F_k_y

            # TODO guess initial active set

        # define QP matrices

        # H = ( Q_k_x     0 )
        #     (     0 Q_k_y )
        self._update_pos_Q() # updates values in Q
        self.pos_H  [ :N+nf,  :N+nf] = self._Q
        self.pos_H  [-N-nf:, -N-nf:] = self._Q

        # g = ( p_k_x )
        #     ( p_k_y )
        self.pos_g  [ :N+nf] = self._get_pos_px()
        self.pos_g  [-N+nf:] = self._get_pos_py()

        # constraints
        #self.pos_A  [...] = 0.0
        #self.pos_lb [...] = 0.0
        #self.pos_ub [...] = 0.0
        #self.pos_lbA[...] = 0.0
        #self.pos_ubA[...] = 0.0

    def _update_pos_Q(self):
        '''
        Update hessian block Q according to walking report

        Q = ( a*Pvu*Pvu + b*Ppu*E*T*E*Ppu + c*Pzu*Pzu + d*I, -c*Pzu*V_kp1  )
            (                                  -c*Pzu*V_kp1, c*V_kp1*V_kp1 )
        '''
        # rename for convenience
        N  = self.N
        nf = self.nf

        # weights
        a = self.a
        b = self.b
        c = self.c
        d = self.d

        # matrices
        Ppu = self.Ppu
        Pvu = self.Pvu
        Pzu = self.Pzu

        V_kp1 = self.V_kp1

        # Q = ([*], * ) = a*Pvu*Pvu + b*Ppu*E*E*Ppu + c*Pzu*Pzu + d*I
        #     ( * , * )
        a = 0; b = N
        c = 0; d = N
        self._Q[a:b,c:d] = a*Pvu.transpose().dot(Pvu) \
                         + c*Pzu.transpose().dot(Pzu) \
                         + d*numpy.eye(N)
                         # TODO How is matrix E defined?
                         # E = (I_? 0 I_?)/2tau_step
                         #+ b*Ppu.transpose()*E.transpose()*E*Ppu \

        # Q = ( * ,[*])
        #     ( * , * )
        a = 0; b = N
        c = N; d = N+nf
        self._Q[a:b,c:d] = -c*Pzu.transpose().dot(V_kp1)

        # Q = (  * , * ) = ( * , [*] )^T
        #     ( [*], * )   ( * ,  *  )
        dummy = self._Q[a:b,c:d].transpose()
        a = N; b = N+nf
        c = 0; d = N
        self._Q[a:b,c:d] = dummy

        # Q = ( * , * )
        #     ( * ,[*])
        a = N; b = N+nf
        c = N; d = N+nf
        self._Q[a:b,c:d] = c*V_kp1.transpose().dot(V_kp1)

    def _get_pos_py(self):
        pass

    def _get_pos_px(self):
        pass

    def _update_pk(self):
        """
        Update pass gradient block p according to walking report

        p = ( a*Pvu*(Pvs*ck - Refk+1 ) + b*Ppu*E*(E*Pps*cx - Refk+1 ) + c*Pzu*(Pzs*ck - vk+1*fk )
            (                                                         -c*Vk+1*(Pzs*ck - vk+1*fk )
        """
        # rename for convenience
        N  = self.N
        nf = self.nf

        # weights
        a = self.a
        b = self.b

        # matrices
        Pvu = self.Pvu
        Ppu = self.Ppu
        Pzu = self.Pzu

        V_kp1 = self.V_kp1

        # p = ([*]) =
        #     ( * )
        a = 0; b = N
        self._p[a:b] = a*Pvu.transpose()*Pvu \
                     + c*Pzu.transpose()*Pzu \
                     + d*numpy.eye(N)
                     #+ b*Ppu.transpose()*E.transpose()*E*Ppu \

        # p = ( * ) =
        #     ([*])
        a = N; b = N+nf
        c = N; d = N+nf
        self._Q[a:b,c:d] = c*V_kp1*V_kp1

    def _solve_qp(self):
        """
        Solve QP first run with init functionality and other runs with warmstart
        """
        sys.stdout.write('Solve for orientations:\n')
        if not self._ori_qp_is_initialized:
            self.ori_qp.init(
                self.ori_H, self.ori_g, self.ori_A,
                self.ori_lb, self.ori_ub,
                self.ori_lbA, self.ori_ubA,
                self.nwsr, self.cpu_time
            )
            self._ori_qp_is_initialized = True
        else:
            self.ori_qp.hotstart(
                self.ori_H, self.ori_g, self.ori_A,
                self.ori_lb, self.ori_ub,
                self.ori_lbA, self.ori_ubA,
                self.nwsr, self.cpu_time
            )

        sys.stdout.write('Solve for positions:\n')
        if not self._pos_qp_is_initialized:
            self.pos_qp.init(
                self.pos_H, self.pos_g, self.pos_A,
                self.pos_lb, self.pos_ub,
                self.pos_lbA, self.pos_ubA,
                self.nwsr, self.cpu_time
            )
            self._pos_qp_is_initialized = True
        else:
            self.pos_qp.hotstart(
                self.pos_H, self.pos_g, self.pos_A,
                self.pos_lb, self.pos_ub,
                self.pos_lbA, self.pos_ubA,
                self.nwsr, self.cpu_time
            )

    def _postprocess_solution(self):
        """ Get solution and put it back into generator data structures """
        # rename for convenience
        N  = self.N
        nf = self.nf

        # orientation primal solution
        self.ori_qp.getPrimalSolution(self.ori_dofs)

        # extract dofs
        # ori_dofs = ( dddC_kp1_q )
        #            (      F_k_q )

        self.dddC_k_q[:] = self.ori_dofs[:N]
        self.F_k_q[:]    = self.ori_dofs[-nf:]

        # position primal solution
        self.pos_qp.getPrimalSolution(self.pos_dofs)

        # extract dofs
        # pos_dofs = ( dddC_kp1_x )
        #            (      F_k_x )
        #            ( dddC_kp1_y )
        #            (      F_k_y )
        self.dddC_k_x[:] = self.pos_dofs[0  :0+N   ]
        self.F_k_x[:]    = self.pos_dofs[0+N:0+N+nf]
        a = N + nf
        self.dddC_k_y[:] = self.pos_dofs[a  :a+N   ]
        self.F_k_y[:]    = self.pos_dofs[a+N:a+N+nf]
