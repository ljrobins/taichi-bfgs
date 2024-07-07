from .spbfgs import vecnorm, rosen as rosen_np, finite_difference_gradient
import numpy as np
from .tibfgs import matnorm, VTYPE, MTYPE, rosen as rosen_ti, two_point_gradient, set_f
import taichi as ti

def test_vecnorm():
    m = np.array([[-1.0, 1.0], [2.0, 3.0]])
    
    @ti.kernel
    def call_vecnorm_ti(ord: ti.f32) -> ti.f32:
        m = MTYPE([[-1.0, 1.0], [2.0, 3.0]])
        return matnorm(m, ord=ord)

    assert np.allclose(call_vecnorm_ti(ti.math.inf), vecnorm(m, ord=np.inf))
    assert np.allclose(call_vecnorm_ti(-ti.math.inf), vecnorm(m, ord=-np.inf))

def test_fdiff():
    from .tibfgs import fprime
    set_f(rosen_ti)

    @ti.kernel
    def call_fdiff() -> VTYPE:
        return fprime(ti.math.vec2([-1.0, 1.0]))
    
    g_ti = call_fdiff()
    g_np = finite_difference_gradient(rosen_np, np.array([-1.0, 1.0], dtype=np.float32), finite_difference_stepsize=1e-4)
    assert np.allclose(g_ti, g_np)

def test_wolfe1():
    xkl = [-1., 1.]
    pkl = [ 3.99940246e+00, -1.49011612e-04]
    gfkl = [-3.99940246e+00, 1.49011612e-04]
    old_fval = 3.991124871148457
    old_old_fval = 4.0
    f = rosen_np

    from .spbfgs import line_search_wolfe1
    myfprime = lambda x: finite_difference_gradient(f, x, finite_difference_stepsize=1e-6)

    alpha_k, fc, gc, _old_fval, _old_old_fval, gfkp1 = line_search_wolfe1(f=f, fprime=myfprime, xk=np.array(xkl), 
    pk=np.array(pkl), gfk=np.array(gfkl), old_fval=old_fval, old_old_fval=old_old_fval, amin=1e-100,
                                          amax=1e100, c1=1e-4, c2=0.9)

    # print(alpha_k, fc, gc, old_fval, old_old_fval, gfkp1)
    # enddd

    from .tibfgs import line_search_wolfe1 as ti_line_search_wolfe1

    @ti.kernel
    def call_ti_line_search():
        xk = VTYPE(xkl)
        pk = VTYPE(pkl)
        gfk = VTYPE(gfkl)
        print(gfk)
        ti_line_search_wolfe1(i=0, xk=xk, pk=pk, gfk=gfk, old_fval=old_fval, old_old_fval=old_old_fval, 
                            amin=1e-100, amax=1e100, c1=1e-4, c2=0.9, xtol=1e-6)
    
    call_ti_line_search()

    # 0.0016836467408263564 2 2 3.991124871148457 4.0 [1.34653055 2.68446298]

def test_dcstep():
    from .spbfgs import dcstep as dcstep_sp
    from .tibfgs import dcstep as dcstep_ti

    stx, fx, dx, sty, fy, dy, stp, fp, dp, brackt, stpmin, stpmax = \
    (0.0, 4.0, -15.99522009389491, 0.0, 4.0, -15.99522009389491, 0.2525377248993902, 100.95257568773, -23.945207713640414, False, 0, 1.2626886244969509)

    tup_sp = dcstep_sp(stx, fx, dx, sty, fy, dy, stp, fp, dp, brackt, stpmin, stpmax)

    @ti.kernel
    def run_ti_dcstep() -> ti.types.vector(n=8, dtype=ti.f32):
        x = ti.Vector(dcstep_ti(stx, fx, dx, sty, fy, dy, stp, fp, dp, brackt, stpmin, stpmax))
        return x
    
    tup_ti = run_ti_dcstep()

    for x,y in zip(tup_sp, tup_ti):
        assert np.allclose(x,y)

def test_dcsearch():
    from .spbfgs import DCSRCH as DCSRCH_np
    from .tibfgs import DCSRCH as DCSRCH_ti

    x0 = np.array([-1.0, 1.0])
    (ftol, gtol, xtol, stpmin, stpmax) = (0.0001, 0.9, 1e-14, 1e-10, 1e+10)

    f = rosen_np
    fprime = lambda x: finite_difference_gradient(f, x, finite_difference_stepsize=1e-6)

    gfk = fprime(x0)

    gval = [gfk]
    gc = [0]
    fc = [0]

    xk = x0
    pk = np.array([3.99940246e+00, -1.49011612e-04])

    def phi(s):
        fc[0] += 1
        return f(xk + s*pk)

    def derphi(s):
        gval[0] = fprime(xk + s*pk)
        gc[0] += 1
        return np.dot(gval[0], pk)

    alpha1, phi0, derphi0, maxiter = 0.2525377248993902, 4.0, -15.99522009389491, 100
    stp, phi1, phi0, task = DCSRCH_np(phi, derphi, ftol, gtol, xtol, stpmin, stpmax)(
        alpha1, phi0=phi0, derphi0=derphi0, maxiter=maxiter
    )
    print('step results np')
    print(stp, phi1, phi0, task)

    @ti.kernel
    def run_ti_dcsrch():
        stp: ti.f32 = 0.0
        phi1: ti.f32 = 0.0
        phi0: ti.f32 = 0.0
        task: ti.u8 = 0
        for _ in range(1):
            stp, phi1, phi0, task = DCSRCH_ti(VTYPE(xk), VTYPE(pk), ftol, gtol, xtol, stpmin, stpmax, i=0).call(
                alpha1, phi0=phi0, derphi0=derphi0, maxiter=maxiter
            )
        print(stp, phi1, phi0, task)
        # return stp, phi1, phi0, task
    
    tup_ti = run_ti_dcsrch()
    print(tup_ti)

    # for x,y in zip(tup_sp, tup_ti):
    #     assert np.allclose(x,y)