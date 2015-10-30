import numpy as np

def recompose_DM(I,modes,numiter=100,x0=None):
    """
    Find the coefficients [a0, a1, a2, ...]
    such that
    I = abs(a0*m[0] + a1*m[1] + ... )**2
    using difference map.
    m should be normalized.
    """
    fmag = np.sqrt(I)
    Nmodes = modes.shape[0]
    relaxfact = 1e-3
    fpower = np.sum(I)
    
    def fproj(psi):
        return fmag * np.exp(1j*np.angle(psi))

    def fproj_relax(psi):
        apsi = np.abs(psi)
        dv = fmag - apsi
        pw = np.sum(np.abs(dv)**2)
        if pw > relaxfact*fpower:
            apsi += (1-relaxfact*fpower/pw)*dv
        return apsi * np.exp(1j*np.angle(psi))

    def cproj(psi):
        c = np.tensordot(psi, modes.conj(), axes=((0,1),(1,2)))
        return np.tensordot(c , modes, axes=(0,0)), c

    if x0 is None:
        c = np.random.normal(size=(Nmodes,)) + 1j*np.random.normal(size=(Nmodes,))
        psi = np.tensordot(c, modes, axes=(0,0))
    else:
        psi = x0
    err = []
    
    ###print sum(abs(cproj(psi)[0] - psi)**2)
    ###print sum(abs(fproj_relax(psi) - psi)**2)
    
    DM = True
    for i in range(numiter):
        #p1 = fproj_relax(psi)
        #if DM:
        #    p2,c = cproj(2*p1 - psi)
        #    df = p2 - p1
        #    psi += df
        #else:
        #    p2,c = cproj(p1)
        #    df = p2 - psi
        #    psi = p2
        p1, c = cproj(psi)
        if DM:
            p2 = fproj_relax(2*p1 - psi)
            df = p2 - p1
            psi += df
        else:
            p2 = fproj_relax(p1)
            df = p2 - psi
            psi = p2
        err.append((np.abs(df)**2).sum())
        ###print i, err[-1]
        if err[-1] < 1e-10:
            break

    return c, err
        
def recompose_ML(I, m):
    """
    Find the coefficients [a0, a1, a2, ...]
    such that
    I = abs(a0*m[0] + a1*m[1] + ... )**2
    using a maximum likelihood method.
    """
    N = len(m)

    sigma = 1./(I+1)
    # or:
    # sigma = np.ones_like(I)

    # Prepare optimization parameters
    A = np.zeros((N,N,N,N), dtype=complex)
    B = np.zeros((N,N), dtype = complex)
    for l in range(N):
        for k in range(N):
            B[k,l] = (sigma*I*m[k]*m[l].conj()).sum()
            for j in range(N):
                for i in range(N):
                    A[i,j,k,l] = (sigma*m[i]*m[k]*(m[j]*m[l]).conj()).sum()

    # Outer loop: try various initial conditions
    ntry = 5
    numiter = 500
    results = []
    sh = (N,)
    tol = 1e-15
    sols = []
    for n in range(ntry):
        c = np.random.normal(size=sh) + 1j*np.random.normal(size=sh)

        # Non-linear CG
        LL = np.inf
        start = True
        for i in range(numiter):
            
            # New negative log-likelihood
            psi = np.tensordot(c, m, axes=(0,0))
            Im = abs(psi)**2
            LLnew = (sigma * (I - Im)**2).sum()
            print '# %8d - L = %8.4e' % (i, LLnew)
            #if (LL - LLnew) < tol * LLnew:
            #    break
            LL = LLnew
            
            # New gradient
            grad = 2*np.tensordot(sigma*(I-Im)*psi, m.conj(), axes=((0,1),(1,2)))

            # New search direction
            if start:
                start = False
                beta = 0
                h = -grad
                grad_nrm = (abs(grad)**2).sum()
            else:
                grad_nrm_new = (abs(grad)**2).sum()
                beta = (grad_nrm_new - np.real(np.vdot(grad_prev, grad))) / grad_nrm
                grad_nrm = grad_nrm_new
                if beta < 0:
                    beta = 0
                print 'beta = %f' % beta
                h *= beta
                h -= grad

            grad_prev = grad.copy()

            ## Minimization
            # Useful quantities
            dpsi = np.tensordot(h, m, axes=(0, 0))
            kappa = psi*dpsi.conj() + psi.conj()*dpsi
            dpsi2 = abs(dpsi)**2
            # Polynomial coefficients
            cA = -2. * (sigma * (I - Im) * kappa).sum()
            cB = 2. * (sigma * (kappa**2 - 2*(I-Im)*dpsi2)).sum()
            cC = 6. * (sigma * kappa*dpsi2).sum()
            cD = 4. * (sigma * dpsi2**2).sum()
            # Find roots
            out = np.roots([cD, cC, cB, cA])
            # Select best root
            out = out[np.isreal(out)]
            if len(out) > 1:
                alpha = np.real(out[np.argmin(abs(out))])
            else:
                alpha = np.real(out[0])
            # Check that we really have a minimum
            LL_change = cA*alpha + (cB/2.)*alpha**2 + (cC/3.)*alpha**3 + (cD/4.)*alpha**4
            print('Change in LL: %s' % str(LL_change))
            # Update c
            c += alpha*h
            
        sols.append(c)
    
    # Here we would do some statistics on sols...
    return sols
    
