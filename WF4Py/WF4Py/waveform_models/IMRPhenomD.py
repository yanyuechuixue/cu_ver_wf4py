#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#    Copyright (c) 2022 Francesco Iacovelli <francesco.iacovelli@unige.ch>
#
#    All rights reserved. Use of this source code is governed by the
#    license that can be found in the LICENSE file.

import cupy as np
import os
from WF4Py import WFutils as utils

from .WFclass_definition import WaveFormModel

##############################################################################
# IMRPhenomD WAVEFORM
##############################################################################

class IMRPhenomD(WaveFormModel):
    """
    IMRPhenomD waveform model.
    
    Relevant references:
        [1] `arXiv:1508.07250 <https://arxiv.org/abs/1508.07250>`_
        
        [2] `arXiv:1508.07253 <https://arxiv.org/abs/1508.07253>`_
    
    :param kwargs: Optional arguments to be passed to the parent class :py:class:`WF4Py.waveform_models.WFclass_definition.WaveFormModel`.
        
    """
    # All is taken from LALSimulation and arXiv:1508.07250, arXiv:1508.07253
    def __init__(self, **kwargs):
        """
        Constructor method
        """
        # Dimensionless frequency (Mf) at which the inspiral amplitude switches to the intermediate amplitude
        self.AMP_fJoin_INS = 0.014
        # Dimensionless frequency (Mf) at which the inspiral phase switches to the intermediate phase
        self.PHI_fJoin_INS = 0.018
        # Dimensionless frequency (Mf) at which we define the end of the waveform
        fcutPar = 0.2
         
        super().__init__('BBH', fcutPar, **kwargs)
        
        self.QNMgrid_a     = np.loadtxt(os.path.join(utils.WFfilesPATH, 'QNMData_a.txt'))
        self.QNMgrid_fring = np.loadtxt(os.path.join(utils.WFfilesPATH, 'QNMData_fring.txt'))
        self.QNMgrid_fdamp = np.loadtxt(os.path.join(utils.WFfilesPATH, 'QNMData_fdamp.txt'))
        
    def Phi(self, f, **kwargs):
        """
        Compute the phase of the GW as a function of frequency, given the events parameters.
        
        :param cupy.ndarray f: Frequency grid on which the phase will be computed, in :math:`\\rm Hz`.
        :param dict(cupy.ndarray, cupy.ndarray, ...) kwargs: Dictionary with arrays containing the parameters of the events to compute the phase of, as in :py:data:`events`.
        :return: GW phase for the chosen events evaluated on the frequency grid.
        :rtype: cupy.ndarray
        
        """
        utils.check_evparams(kwargs, checktidal=self.is_tidal)
        M = kwargs['Mc']/(kwargs['eta']**(3./5.))
        eta = kwargs['eta']
        eta2 = eta*eta # These can speed up a bit, we call them multiple times
        etaInv = 1./eta
        chi1, chi2 = kwargs['chi1z'], kwargs['chi2z']
        
        QuadMon1, QuadMon2 = np.ones(M.shape), np.ones(M.shape)
        
        chi12, chi22 = chi1*chi1, chi2*chi2
        chi1dotchi2  = chi1*chi2
        
        Seta = np.sqrt(1.0 - 4.0*eta)
        SetaPlus1 = 1.0 + Seta
        chi_s = 0.5 * (chi1 + chi2)
        chi_a = 0.5 * (chi1 - chi2)
        q = 0.5*(1.0 + Seta - 2.0*eta)/eta
        chi_s2, chi_a2 = chi_s*chi_s, chi_a*chi_a
        chi1dotchi2    = chi1*chi2
        chi_sdotchi_a  = chi_s*chi_a
        # These are m1/Mtot and m2/Mtot
        m1ByM = 0.5 * (1.0 + Seta)
        m2ByM = 0.5 * (1.0 - Seta)
        # We work in dimensionless frequency M*f, not f
        fgrid = M*utils.GMsun_over_c3*f
        # As in arXiv:1508.07253 eq. (4) and LALSimIMRPhenomD_internals.c line 97
        chiPN = (chi_s * (1.0 - eta * 76.0 / 113.0) + Seta * chi_a)
        xi = - 1.0 + chiPN
        # Compute final spin and radiated energy
        aeff = self._finalspin(eta, chi1, chi2)
        Erad = self._radiatednrg(eta, chi1, chi2)
        # Compute ringdown and damping frequencies from interpolators
        fring = np.interp(aeff, self.QNMgrid_a, self.QNMgrid_fring) / (1.0 - Erad)
        fdamp = np.interp(aeff, self.QNMgrid_a, self.QNMgrid_fdamp) / (1.0 - Erad)
        
        # Compute sigma coefficients appearing in arXiv:1508.07253 eq. (28)
        # They derive from a fit, whose numerical coefficients are in arXiv:1508.07253 Tab. 5
        sigma1 = 2096.551999295543 + 1463.7493168261553*eta + (1312.5493286098522 + 18307.330017082117*eta - 43534.1440746107*eta2 + (-833.2889543511114 + 32047.31997183187*eta - 108609.45037520859*eta2)*xi + (452.25136398112204 + 8353.439546391714*eta - 44531.3250037322*eta2)*xi*xi)*xi
        sigma2 = -10114.056472621156 - 44631.01109458185*eta + (-6541.308761668722 - 266959.23419307504*eta + 686328.3229317984*eta2 + (3405.6372187679685 - 437507.7208209015*eta + 1.6318171307344697e6*eta2)*xi + (-7462.648563007646 - 114585.25177153319*eta + 674402.4689098676*eta2)*xi*xi)*xi
        sigma3 = 22933.658273436497 + 230960.00814979506*eta + (14961.083974183695 + 1.1940181342318142e6*eta - 3.1042239693052764e6*eta2 + (-3038.166617199259 + 1.8720322849093592e6*eta - 7.309145012085539e6*eta2)*xi + (42738.22871475411 + 467502.018616601*eta - 3.064853498512499e6*eta2)*xi*xi)*xi
        sigma4 = -14621.71522218357 - 377812.8579387104*eta + (-9608.682631509726 - 1.7108925257214056e6*eta + 4.332924601416521e6*eta2 + (-22366.683262266528 - 2.5019716386377467e6*eta + 1.0274495902259542e7*eta2)*xi + (-85360.30079034246 - 570025.3441737515*eta + 4.396844346849777e6*eta2)*xi*xi)*xi
        
        # Compute beta coefficients appearing in arXiv:1508.07253 eq. (16)
        # They derive from a fit, whose numerical coefficients are in arXiv:1508.07253 Tab. 5
        beta1 = 97.89747327985583 - 42.659730877489224*eta + (153.48421037904913 - 1417.0620760768954*eta + 2752.8614143665027*eta2 + (138.7406469558649 - 1433.6585075135881*eta + 2857.7418952430758*eta2)*xi + (41.025109467376126 - 423.680737974639*eta + 850.3594335657173*eta2)*xi*xi)*xi
        beta2 = -3.282701958759534 - 9.051384468245866*eta + (-12.415449742258042 + 55.4716447709787*eta - 106.05109938966335*eta2 + (-11.953044553690658 + 76.80704618365418*eta - 155.33172948098394*eta2)*xi + (-3.4129261592393263 + 25.572377569952536*eta - 54.408036707740465*eta2)*xi*xi)*xi
        beta3 = -0.000025156429818799565 + 0.000019750256942201327*eta + (-0.000018370671469295915 + 0.000021886317041311973*eta + 0.00008250240316860033*eta2 + (7.157371250566708e-6 - 0.000055780000112270685*eta + 0.00019142082884072178*eta2)*xi + (5.447166261464217e-6 - 0.00003220610095021982*eta + 0.00007974016714984341*eta2)*xi*xi)*xi
        
        # Compute alpha coefficients appearing in arXiv:1508.07253 eq. (14)
        # They derive from a fit, whose numerical coefficients are in arXiv:1508.07253 Tab. 5
        alpha1 = 43.31514709695348 + 638.6332679188081*eta + (-32.85768747216059 + 2415.8938269370315*eta - 5766.875169379177*eta2 + (-61.85459307173841 + 2953.967762459948*eta - 8986.29057591497*eta2)*xi + (-21.571435779762044 + 981.2158224673428*eta - 3239.5664895930286*eta2)*xi*xi)*xi
        alpha2 = -0.07020209449091723 - 0.16269798450687084*eta + (-0.1872514685185499 + 1.138313650449945*eta - 2.8334196304430046*eta2 + (-0.17137955686840617 + 1.7197549338119527*eta - 4.539717148261272*eta2)*xi + (-0.049983437357548705 + 0.6062072055948309*eta - 1.682769616644546*eta2)*xi*xi)*xi
        alpha3 = 9.5988072383479 - 397.05438595557433*eta + (16.202126189517813 - 1574.8286986717037*eta + 3600.3410843831093*eta2 + (27.092429659075467 - 1786.482357315139*eta + 5152.919378666511*eta2)*xi + (11.175710130033895 - 577.7999423177481*eta + 1808.730762932043*eta2)*xi*xi)*xi
        alpha4 = -0.02989487384493607 + 1.4022106448583738*eta + (-0.07356049468633846 + 0.8337006542278661*eta + 0.2240008282397391*eta2 + (-0.055202870001177226 + 0.5667186343606578*eta + 0.7186931973380503*eta2)*xi + (-0.015507437354325743 + 0.15750322779277187*eta + 0.21076815715176228*eta2)*xi*xi)*xi
        alpha5 = 0.9974408278363099 - 0.007884449714907203*eta + (-0.059046901195591035 + 1.3958712396764088*eta - 4.516631601676276*eta2 + (-0.05585343136869692 + 1.7516580039343603*eta - 5.990208965347804*eta2)*xi + (-0.017945336522161195 + 0.5965097794825992*eta - 2.0608879367971804*eta2)*xi*xi)*xi
        
        # Compute the TF2 phase coefficients and put them in a dictionary (spin effects are included up to 3.5PN)
        TF2coeffs = {}
        TF2OverallAmpl = 3./(128. * eta)
        
        TF2coeffs['zero'] = 1.
        TF2coeffs['one'] = 0.
        TF2coeffs['two'] = 3715./756. + (55.*eta)/9.
        TF2coeffs['three'] = -16.*np.pi + (113.*Seta*chi_a)/3. + (113./3. - (76.*eta)/3.)*chi_s
        # For 2PN coeff we use chi1 and chi2 so to have the quadrupole moment explicitly appearing
        TF2coeffs['four'] = 5.*(3058.673/7.056 + 5429./7.*eta+617.*eta2)/72. + 247./4.8*eta*chi1dotchi2 -721./4.8*eta*chi1dotchi2 + (-720./9.6*QuadMon1 + 1./9.6)*m1ByM*m1ByM*chi12 + (-720./9.6*QuadMon2 + 1./9.6)*m2ByM*m2ByM*chi22 + (240./9.6*QuadMon1 - 7./9.6)*m1ByM*m1ByM*chi12 + (240./9.6*QuadMon2 - 7./9.6)*m2ByM*m2ByM*chi22
        # This part is common to 5 and 5log, avoid recomputing
        TF2_5coeff_tmp = (732985./2268. - 24260.*eta/81. - 340.*eta2/9.)*chi_s + (732985./2268. + 140.*eta/9.)*Seta*chi_a
        TF2coeffs['five'] = (38645.*np.pi/756. - 65.*np.pi*eta/9. - TF2_5coeff_tmp)
        TF2coeffs['five_log'] = (38645.*np.pi/756. - 65.*np.pi*eta/9. - TF2_5coeff_tmp)*3.
        # For 3PN coeff we use chi1 and chi2 so to have the quadrupole moment explicitly appearing
        TF2coeffs['six'] = 11583.231236531/4.694215680 - 640./3.*np.pi*np.pi - 684.8/2.1*np.euler_gamma + eta*(-15737.765635/3.048192 + 225.5/1.2*np.pi*np.pi) + eta2*76.055/1.728 - eta2*eta*127.825/1.296 - np.log(4.)*684.8/2.1 + np.pi*chi1*m1ByM*(1490./3. + m1ByM*260.) + np.pi*chi2*m2ByM*(1490./3. + m2ByM*260.) + (326.75/1.12 + 557.5/1.8*eta)*eta*chi1dotchi2 + (4703.5/8.4+2935./6.*m1ByM-120.*m1ByM*m1ByM)*m1ByM*m1ByM*QuadMon1*chi12 + (-4108.25/6.72-108.5/1.2*m1ByM+125.5/3.6*m1ByM*m1ByM)*m1ByM*m1ByM*chi12 + (4703.5/8.4+2935./6.*m2ByM-120.*m2ByM*m2ByM)*m2ByM*m2ByM*QuadMon2*chi22 + (-4108.25/6.72-108.5/1.2*m2ByM+125.5/3.6*m2ByM*m2ByM)*m2ByM*m2ByM*chi22
        TF2coeffs['six_log'] = -6848./21.
        TF2coeffs['seven'] = 77096675.*np.pi/254016. + 378515.*np.pi*eta/1512.- 74045.*np.pi*eta2/756. + (-25150083775./3048192. + 10566655595.*eta/762048. - 1042165.*eta2/3024. + 5345.*eta2*eta/36.)*chi_s + Seta*((-25150083775./3048192. + 26804935.*eta/6048. - 1985.*eta2/48.)*chi_a)
        # Remove this part since it was not available when IMRPhenomD was tuned
        TF2coeffs['six'] = TF2coeffs['six'] - ((326.75/1.12 + 557.5/1.8*eta)*eta*chi1dotchi2 + ((4703.5/8.4+2935./6.*m1ByM-120.*m1ByM*m1ByM) + (-4108.25/6.72-108.5/1.2*m1ByM+125.5/3.6*m1ByM*m1ByM))*m1ByM*m1ByM*chi12 + ((4703.5/8.4+2935./6.*m2ByM-120.*m2ByM*m2ByM) + (-4108.25/6.72-108.5/1.2*m2ByM+125.5/3.6*m2ByM*m2ByM))*m2ByM*m2ByM*chi22)
        # Now translate into inspiral coefficients, label with the power in front of which they appear
        PhiInspcoeffs = {}
        
        PhiInspcoeffs['initial_phasing'] = TF2coeffs['five']*TF2OverallAmpl
        PhiInspcoeffs['two_thirds'] = TF2coeffs['seven']*TF2OverallAmpl*(np.pi**(2./3.))
        PhiInspcoeffs['third'] = TF2coeffs['six']*TF2OverallAmpl*(np.pi**(1./3.))
        PhiInspcoeffs['third_log'] = TF2coeffs['six_log']*TF2OverallAmpl*(np.pi**(1./3.))
        PhiInspcoeffs['log'] = TF2coeffs['five_log']*TF2OverallAmpl
        PhiInspcoeffs['min_third'] = TF2coeffs['four']*TF2OverallAmpl*(np.pi**(-1./3.))
        PhiInspcoeffs['min_two_thirds'] = TF2coeffs['three']*TF2OverallAmpl*(np.pi**(-2./3.))
        PhiInspcoeffs['min_one'] = TF2coeffs['two']*TF2OverallAmpl/np.pi
        PhiInspcoeffs['min_four_thirds'] = TF2coeffs['one']*TF2OverallAmpl*(np.pi**(-4./3.))
        PhiInspcoeffs['min_five_thirds'] = TF2coeffs['zero']*TF2OverallAmpl*(np.pi**(-5./3.))
        PhiInspcoeffs['one'] = sigma1
        PhiInspcoeffs['four_thirds'] = sigma2 * 0.75
        PhiInspcoeffs['five_thirds'] = sigma3 * 0.6
        PhiInspcoeffs['two'] = sigma4 * 0.5
        
        #Now compute the coefficients to align the three parts
        
        fInsJoin = self.PHI_fJoin_INS
        fMRDJoin = 0.5*fring
        
        # First the Inspiral - Intermediate: we compute C1Int and C2Int coeffs
        # Equations to solve for to get C(1) continuous join
        # PhiIns (f)  =   PhiInt (f) + C1Int + C2Int f
        # Joining at fInsJoin
        # PhiIns (fInsJoin)  =   PhiInt (fInsJoin) + C1Int + C2Int fInsJoin
        # PhiIns'(fInsJoin)  =   PhiInt'(fInsJoin) + C2Int
        # This is the first derivative wrt f of the inspiral phase computed at fInsJoin, first add the PN contribution and then the higher order calibrated terms
        DPhiIns = (2.0*TF2coeffs['seven']*TF2OverallAmpl*((np.pi*fInsJoin)**(7./3.)) + (TF2coeffs['six']*TF2OverallAmpl + TF2coeffs['six_log']*TF2OverallAmpl * (1.0 + np.log(np.pi*fInsJoin)/3.))*((np.pi*fInsJoin)**(2.)) + TF2coeffs['five_log']*TF2OverallAmpl*((np.pi*fInsJoin)**(5./3.)) - TF2coeffs['four']*TF2OverallAmpl*((np.pi*fInsJoin)**(4./3.)) - 2.*TF2coeffs['three']*TF2OverallAmpl*(np.pi*fInsJoin) - 3.*TF2coeffs['two']*TF2OverallAmpl*((np.pi*fInsJoin)**(2./3.)) - 4.*TF2coeffs['one']*TF2OverallAmpl*((np.pi*fInsJoin)**(1./3.)) - 5.*TF2coeffs['zero']*TF2OverallAmpl)*np.pi/(3.*((np.pi*fInsJoin)**(8./3.)))
        DPhiIns = DPhiIns + (sigma1 + sigma2*(fInsJoin**(1./3.)) + sigma3*(fInsJoin**(2./3.)) + sigma4*fInsJoin)/eta
        # This is the first derivative of the Intermediate phase computed at fInsJoin
        DPhiInt = (beta1 + beta3/(fInsJoin**4) + beta2/fInsJoin)/eta
        
        C2Int = DPhiIns - DPhiInt
        
        # This is the inspiral phase computed at fInsJoin
        PhiInsJoin = PhiInspcoeffs['initial_phasing'] + PhiInspcoeffs['two_thirds']*(fInsJoin**(2./3.)) + PhiInspcoeffs['third']*(fInsJoin**(1./3.)) + PhiInspcoeffs['third_log']*(fInsJoin**(1./3.))*np.log(np.pi*fInsJoin)/3. + PhiInspcoeffs['log']*np.log(np.pi*fInsJoin)/3. + PhiInspcoeffs['min_third']*(fInsJoin**(-1./3.)) + PhiInspcoeffs['min_two_thirds']*(fInsJoin**(-2./3.)) + PhiInspcoeffs['min_one']/fInsJoin + PhiInspcoeffs['min_four_thirds']*(fInsJoin**(-4./3.)) + PhiInspcoeffs['min_five_thirds']*(fInsJoin**(-5./3.)) + (PhiInspcoeffs['one']*fInsJoin + PhiInspcoeffs['four_thirds']*(fInsJoin**(4./3.)) + PhiInspcoeffs['five_thirds']*(fInsJoin**(5./3.)) + PhiInspcoeffs['two']*fInsJoin*fInsJoin)/eta
        # This is the Intermediate phase computed at fInsJoin
        PhiIntJoin = beta1*fInsJoin - beta3/(3.*fInsJoin*fInsJoin*fInsJoin) + beta2*np.log(fInsJoin)
        
        C1Int = PhiInsJoin - PhiIntJoin/eta - C2Int*fInsJoin
        
        # Now the same for Intermediate - Merger-Ringdown: we also need a temporary Intermediate Phase function
        PhiIntTempVal  = (beta1*fMRDJoin - beta3/(3.*fMRDJoin*fMRDJoin*fMRDJoin) + beta2*np.log(fMRDJoin))/eta + C1Int + C2Int*fMRDJoin
        DPhiIntTempVal = C2Int + (beta1 + beta3/(fMRDJoin**4) + beta2/fMRDJoin)/eta
        DPhiMRDVal     = (alpha1 + alpha2/(fMRDJoin*fMRDJoin) + alpha3/(fMRDJoin**(1./4.)) + alpha4/(fdamp*(1. + (fMRDJoin - alpha5*fring)*(fMRDJoin - alpha5*fring)/(fdamp*fdamp))))/eta
        PhiMRJoinTemp  = -(alpha2/fMRDJoin) + (4.0/3.0) * (alpha3 * (fMRDJoin**(3./4.))) + alpha1 * fMRDJoin + alpha4 * np.arctan((fMRDJoin - alpha5 * fring)/fdamp)
        
        C2MRD = DPhiIntTempVal - DPhiMRDVal
        C1MRD = PhiIntTempVal - PhiMRJoinTemp/eta - C2MRD*fMRDJoin
        
        # Time shift so that peak amplitude is approximately at t=0
        gamma2 = 1.010344404799477 + 0.0008993122007234548*eta + (0.283949116804459 - 4.049752962958005*eta + 13.207828172665366*eta2 + (0.10396278486805426 - 7.025059158961947*eta + 24.784892370130475*eta2)*xi + (0.03093202475605892 - 2.6924023896851663*eta + 9.609374464684983*eta2)*xi*xi)*xi
        gamma3 = 1.3081615607036106 - 0.005537729694807678*eta +(-0.06782917938621007 - 0.6689834970767117*eta + 3.403147966134083*eta2 + (-0.05296577374411866 - 0.9923793203111362*eta + 4.820681208409587*eta2)*xi + (-0.006134139870393713 - 0.38429253308696365*eta + 1.7561754421985984*eta2)*xi*xi)*xi
        fpeak = np.where(gamma2 >= 1.0, np.fabs(fring - (fdamp*gamma3)/gamma2), np.fabs(fring + (fdamp*(-1.0 + np.sqrt(1.0 - gamma2*gamma2))*gamma3)/gamma2))
        
        t0 = (alpha1 + alpha2/(fpeak*fpeak) + alpha3/(fpeak**(1./4.)) + alpha4/(fdamp*(1. + (fpeak - alpha5*fring)*(fpeak - alpha5*fring)/(fdamp*fdamp))))/eta
        
        # LAL sets fRef as the minimum frequency, do the same
        fRef   = np.amin(fgrid, axis=0)
        phiRef = np.where(fRef < self.PHI_fJoin_INS, PhiInspcoeffs['initial_phasing'] + PhiInspcoeffs['two_thirds']*(fRef**(2./3.)) + PhiInspcoeffs['third']*(fRef**(1./3.)) + PhiInspcoeffs['third_log']*(fRef**(1./3.))*np.log(np.pi*fRef)/3. + PhiInspcoeffs['log']*np.log(np.pi*fRef)/3. + PhiInspcoeffs['min_third']*(fRef**(-1./3.)) + PhiInspcoeffs['min_two_thirds']*(fRef**(-2./3.)) + PhiInspcoeffs['min_one']/fRef + PhiInspcoeffs['min_four_thirds']*(fRef**(-4./3.)) + PhiInspcoeffs['min_five_thirds']*(fRef**(-5./3.)) + (PhiInspcoeffs['one']*fRef + PhiInspcoeffs['four_thirds']*(fRef**(4./3.)) + PhiInspcoeffs['five_thirds']*(fRef**(5./3.)) + PhiInspcoeffs['two']*fRef*fRef)/eta, np.where(fRef<fMRDJoin, (beta1*fRef - beta3/(3.*fRef*fRef*fRef) + beta2*np.log(fRef))/eta + C1Int + C2Int*fRef, np.where(fRef < self.fcutPar, (-(alpha2/fRef) + (4.0/3.0) * (alpha3 * (fRef**(3./4.))) + alpha1 * fRef + alpha4 * np.arctan((fRef - alpha5 * fring)/fdamp))/eta + C1MRD + C2MRD*fRef,0.)))

        phis = np.where(fgrid < self.PHI_fJoin_INS, PhiInspcoeffs['initial_phasing'] + PhiInspcoeffs['two_thirds']*(fgrid**(2./3.)) + PhiInspcoeffs['third']*(fgrid**(1./3.)) + PhiInspcoeffs['third_log']*(fgrid**(1./3.))*np.log(np.pi*fgrid)/3. + PhiInspcoeffs['log']*np.log(np.pi*fgrid)/3. + PhiInspcoeffs['min_third']*(fgrid**(-1./3.)) + PhiInspcoeffs['min_two_thirds']*(fgrid**(-2./3.)) + PhiInspcoeffs['min_one']/fgrid + PhiInspcoeffs['min_four_thirds']*(fgrid**(-4./3.)) + PhiInspcoeffs['min_five_thirds']*(fgrid**(-5./3.)) + (PhiInspcoeffs['one']*fgrid + PhiInspcoeffs['four_thirds']*(fgrid**(4./3.)) + PhiInspcoeffs['five_thirds']*(fgrid**(5./3.)) + PhiInspcoeffs['two']*fgrid*fgrid)/eta, np.where(fgrid<fMRDJoin, (beta1*fgrid - beta3/(3.*fgrid*fgrid*fgrid) + beta2*np.log(fgrid))/eta + C1Int + C2Int*fgrid, np.where(fgrid < self.fcutPar, (-(alpha2/fgrid) + (4.0/3.0) * (alpha3 * (fgrid**(3./4.))) + alpha1 * fgrid + alpha4 * np.arctan((fgrid - alpha5 * fring)/fdamp))/eta + C1MRD + C2MRD*fgrid,0.)))
        
        return phis + np.where(fgrid < self.fcutPar, - t0*(fgrid - fRef) - phiRef, 0.)
        
    def Ampl(self, f, **kwargs):
        """
        Compute the amplitude of the GW as a function of frequency, given the events parameters.
        
        :param cupy.ndarray f: Frequency grid on which the phase will be computed, in :math:`\\rm Hz`.
        :param dict(cupy.ndarray, cupy.ndarray, ...) kwargs: Dictionary with arrays containing the parameters of the events to compute the amplitude of, as in :py:data:`events`.
        :return: GW amplitude for the chosen events evaluated on the frequency grid.
        :rtype: cupy.ndarray
        
        """
        utils.check_evparams(kwargs, checktidal=self.is_tidal)
        # Useful quantities
        M = kwargs['Mc']/(kwargs['eta']**(3./5.))
        eta = kwargs['eta']
        eta2 = eta*eta # This can speed up a bit, we call it multiple times
        chi1, chi2 = kwargs['chi1z'], kwargs['chi2z']
        chi12, chi22 = chi1*chi1, chi2*chi2
        Seta = np.sqrt(1.0 - 4.0*eta)
        SetaPlus1 = 1.0 + Seta
        chi_s     = 0.5 * (chi1 + chi2)
        chi_a     = 0.5 * (chi1 - chi2)
        # We work in dimensionless frequency M*f, not f
        fgrid = M*utils.GMsun_over_c3*f
        # As in arXiv:1508.07253 eq. (4) and LALSimIMRPhenomD_internals.c line 97
        chiPN = (chi_s * (1.0 - eta * 76.0 / 113.0) + Seta * chi_a)
        xi = -1.0 + chiPN
        # Compute final spin and radiated energy
        aeff = self._finalspin(eta, chi1, chi2)
        Erad = self._radiatednrg(eta, chi1, chi2)
        # Compute ringdown and damping frequencies from interpolators
        fring = np.interp(aeff, self.QNMgrid_a, self.QNMgrid_fring) / (1.0 - Erad)
        fdamp = np.interp(aeff, self.QNMgrid_a, self.QNMgrid_fdamp) / (1.0 - Erad)
        # Compute coefficients gamma appearing in arXiv:1508.07253 eq. (19), the numerical coefficients are in Tab. 5
        gamma1 = 0.006927402739328343 + 0.03020474290328911*eta + (0.006308024337706171 - 0.12074130661131138*eta + 0.26271598905781324*eta2 + (0.0034151773647198794 - 0.10779338611188374*eta + 0.27098966966891747*eta2)*xi+ (0.0007374185938559283 - 0.02749621038376281*eta + 0.0733150789135702*eta2)*xi*xi)*xi
        gamma2 = 1.010344404799477 + 0.0008993122007234548*eta + (0.283949116804459 - 4.049752962958005*eta + 13.207828172665366*eta2 + (0.10396278486805426 - 7.025059158961947*eta + 24.784892370130475*eta2)*xi + (0.03093202475605892 - 2.6924023896851663*eta + 9.609374464684983*eta2)*xi*xi)*xi
        gamma3 = 1.3081615607036106 - 0.005537729694807678*eta +(-0.06782917938621007 - 0.6689834970767117*eta + 3.403147966134083*eta2 + (-0.05296577374411866 - 0.9923793203111362*eta + 4.820681208409587*eta2)*xi + (-0.006134139870393713 - 0.38429253308696365*eta + 1.7561754421985984*eta2)*xi*xi)*xi
        # Compute fpeak, from arXiv:1508.07253 eq. (20), we remove the square root term in case it is complex
        fpeak = np.where(gamma2 >= 1.0, np.fabs(fring - (fdamp*gamma3)/gamma2), fring + (fdamp*(-1.0 + np.sqrt(1.0 - gamma2*gamma2))*gamma3)/gamma2)
        # Compute coefficients rho appearing in arXiv:1508.07253 eq. (30), the numerical coefficients are in Tab. 5
        rho1 = 3931.8979897196696 - 17395.758706812805*eta + (3132.375545898835 + 343965.86092361377*eta - 1.2162565819981997e6*eta2 + (-70698.00600428853 + 1.383907177859705e6*eta - 3.9662761890979446e6*eta2)*xi + (-60017.52423652596 + 803515.1181825735*eta - 2.091710365941658e6*eta2)*xi*xi)*xi
        rho2 = -40105.47653771657 + 112253.0169706701*eta + (23561.696065836168 - 3.476180699403351e6*eta + 1.137593670849482e7*eta2 + (754313.1127166454 - 1.308476044625268e7*eta + 3.6444584853928134e7*eta2)*xi + (596226.612472288 - 7.4277901143564405e6*eta + 1.8928977514040343e7*eta2)*xi*xi)*xi
        rho3 = 83208.35471266537 - 191237.7264145924*eta + (-210916.2454782992 + 8.71797508352568e6*eta - 2.6914942420669552e7*eta2 + (-1.9889806527362722e6 + 3.0888029960154563e7*eta - 8.390870279256162e7*eta2)*xi + (-1.4535031953446497e6 + 1.7063528990822166e7*eta - 4.2748659731120914e7*eta2)*xi*xi)*xi
        # Compute coefficients delta appearing in arXiv:1508.07253 eq. (21)
        f1Interm = self.AMP_fJoin_INS
        f3Interm = fpeak
        dfInterm = 0.5*(f3Interm - f1Interm)
        f2Interm = f1Interm + dfInterm
        # First write the inspiral coefficients, we put them in a dictionary and label with the power in front of which they appear
        amp0 = np.sqrt(2.0*eta/3.0)*(np.pi**(-1./6.))
        Acoeffs = {}
        Acoeffs['two_thirds'] = ((-969. + 1804.*eta)*(np.pi**(2./3.)))/672.
        Acoeffs['one'] = ((chi1*(81.*SetaPlus1 - 44.*eta) + chi2*(81. - 81.*Seta - 44.*eta))*np.pi)/48.
        Acoeffs['four_thirds'] = ((-27312085.0 - 10287648.*chi22 - 10287648.*chi12*SetaPlus1 + 10287648.*chi22*Seta+ 24.*(-1975055. + 857304.*chi12 - 994896.*chi1*chi2 + 857304.*chi22)*eta+ 35371056*eta2)* (np.pi**(4./3.)))/8.128512e6
        Acoeffs['five_thirds'] = ((np.pi**(5./3.)) * (chi2*(-285197.*(-1. + Seta) + 4.*(-91902. + 1579.*Seta)*eta - 35632.*eta2) + chi1*(285197.*SetaPlus1 - 4.*(91902. + 1579.*Seta)*eta - 35632.*eta2) + 42840.*(-1.0 + 4.*eta)*np.pi)) / 32256.
        Acoeffs['two'] = - ((np.pi**2.)*(-336.*(-3248849057.0 + 2943675504.*chi12 - 3339284256.*chi1*chi2 + 2943675504.*chi22)*eta2 - 324322727232.*eta2*eta - 7.*(-177520268561. + 107414046432.*chi22 + 107414046432.*chi12*SetaPlus1 - 107414046432.*chi22*Seta + 11087290368.*(chi1 + chi2 + chi1*Seta - chi2*Seta)*np.pi ) + 12.*eta*(-545384828789. - 176491177632.*chi1*chi2 + 202603761360.*chi22 + 77616.*chi12*(2610335. + 995766.*Seta) - 77287373856.*chi22*Seta + 5841690624.*(chi1 + chi2)*np.pi + 21384760320.*np.pi*np.pi)))/6.0085960704e10
        Acoeffs['seven_thirds'] = rho1
        Acoeffs['eight_thirds'] = rho2
        Acoeffs['three'] = rho3
        # v1 is the inspiral model evaluated at f1Interm
        v1 = 1. + (f1Interm**(2./3.))*Acoeffs['two_thirds'] + (f1Interm**(4./3.)) * Acoeffs['four_thirds'] + (f1Interm**(5./3.)) *  Acoeffs['five_thirds'] + (f1Interm**(7./3.)) * Acoeffs['seven_thirds'] + (f1Interm**(8./3.)) * Acoeffs['eight_thirds'] + f1Interm * (Acoeffs['one'] + f1Interm * Acoeffs['two'] + f1Interm*f1Interm * Acoeffs['three'])
        # d1 is the derivative of the inspiral model evaluated at f1
        d1 = ((-969. + 1804.*eta)*(np.pi**(2./3.)))/(1008.*(f1Interm**(1./3.))) + ((chi1*(81.*SetaPlus1 - 44.*eta) + chi2*(81. - 81.*Seta - 44.*eta))*np.pi)/48. + ((-27312085. - 10287648.*chi22 - 10287648.*chi12*SetaPlus1 + 10287648.*chi22*Seta + 24.*(-1975055. + 857304.*chi12 - 994896.*chi1*chi2 + 857304.*chi22)*eta + 35371056.*eta2)*(f1Interm**(1./3.))*(np.pi**(4./3.)))/6.096384e6 + (5.*(f1Interm**(2./3.))*(np.pi**(5./3.))*(chi2*(-285197.*(-1 + Seta)+ 4.*(-91902. + 1579.*Seta)*eta - 35632.*eta2) + chi1*(285197.*SetaPlus1- 4.*(91902. + 1579.*Seta)*eta - 35632.*eta2) + 42840.*(-1 + 4*eta)*np.pi))/96768.- (f1Interm*np.pi*np.pi*(-336.*(-3248849057.0 + 2943675504.*chi12 - 3339284256.*chi1*chi2 + 2943675504.*chi22)*eta2 - 324322727232.*eta2*eta - 7.*(-177520268561. + 107414046432.*chi22 + 107414046432.*chi12*SetaPlus1 - 107414046432.*chi22*Seta+ 11087290368*(chi1 + chi2 + chi1*Seta - chi2*Seta)*np.pi)+ 12.*eta*(-545384828789.0 - 176491177632.*chi1*chi2 + 202603761360.*chi22 + 77616.*chi12*(2610335. + 995766.*Seta)- 77287373856.*chi22*Seta + 5841690624.*(chi1 + chi2)*np.pi + 21384760320*np.pi*np.pi)))/3.0042980352e10+ (7.0/3.0)*(f1Interm**(4./3.))*rho1 + (8.0/3.0)*(f1Interm**(5./3.))*rho2 + 3.*(f1Interm*f1Interm)*rho3
        # v3 is the merger-ringdown model (eq. (19) of arXiv:1508.07253) evaluated at f3
        v3 = np.exp(-(f3Interm - fring)*gamma2/(fdamp*gamma3))* (fdamp*gamma3*gamma1) / ((f3Interm - fring)*(f3Interm - fring) + fdamp*gamma3*fdamp*gamma3)
        # d2 is the derivative of the merger-ringdown model evaluated at f3
        d2 = ((-2.*fdamp*(f3Interm - fring)*gamma3*gamma1) / ((f3Interm - fring)*(f3Interm - fring) + fdamp*gamma3*fdamp*gamma3) - (gamma2*gamma1))/(np.exp((f3Interm - fring)*gamma2/(fdamp*gamma3)) * ((f3Interm - fring)*(f3Interm - fring) + fdamp*gamma3*fdamp*gamma3))
        # v2 is the value of the amplitude evaluated at f2. They come from the fit of the collocation points in the intermediate region
        v2 = 0.8149838730507785 + 2.5747553517454658*eta + (1.1610198035496786 - 2.3627771785551537*eta + 6.771038707057573*eta2 + (0.7570782938606834 - 2.7256896890432474*eta + 7.1140380397149965*eta2)*xi + (0.1766934149293479 - 0.7978690983168183*eta + 2.1162391502005153*eta2)*xi*xi)*xi
        # Now some definitions to speed up
        f1  = f1Interm
        f2  = f2Interm
        f3  = f3Interm
        f12 = f1Interm*f1Interm
        f13 = f1Interm*f12;
        f14 = f1Interm*f13;
        f15 = f1Interm*f14;
        f22 = f2Interm*f2Interm;
        f23 = f2Interm*f22;
        f24 = f2Interm*f23;
        f32 = f3Interm*f3Interm;
        f33 = f3Interm*f32;
        f34 = f3Interm*f33;
        f35 = f3Interm*f34;
        # Finally cnpute the deltas
        delta0 = -((d2*f15*f22*f3 - 2.*d2*f14*f23*f3 + d2*f13*f24*f3 - d2*f15*f2*f32 + d2*f14*f22*f32 - d1*f13*f23*f32 + d2*f13*f23*f32 + d1*f12*f24*f32 - d2*f12*f24*f32 + d2*f14*f2*f33 + 2.*d1*f13*f22*f33 - 2.*d2*f13*f22*f33 - d1*f12*f23*f33 + d2*f12*f23*f33 - d1*f1*f24*f33 - d1*f13*f2*f34 - d1*f12*f22*f34 + 2.*d1*f1*f23*f34 + d1*f12*f2*f35 - d1*f1*f22*f35 + 4.*f12*f23*f32*v1 - 3.*f1*f24*f32*v1 - 8.*f12*f22*f33*v1 + 4.*f1*f23*f33*v1 + f24*f33*v1 + 4.*f12*f2*f34*v1 + f1*f22*f34*v1 - 2.*f23*f34*v1 - 2.*f1*f2*f35*v1 + f22*f35*v1 - f15*f32*v2 + 3.*f14*f33*v2 - 3.*f13*f34*v2 + f12*f35*v2 - f15*f22*v3 + 2.*f14*f23*v3 - f13*f24*v3 + 2.*f15*f2*f3*v3 - f14*f22*f3*v3 - 4.*f13*f23*f3*v3 + 3.*f12*f24*f3*v3 - 4.*f14*f2*f32*v3 + 8.*f13*f22*f32*v3 - 4.*f12*f23*f32*v3) / ((f1 - f2)*(f1 - f2)*(f1 - f3)*(f1 - f3)*(f1 - f3)*(f3 - f2)*(f3 - f2)))
        delta0 = -((d2*f15*f22*f3 - 2.*d2*f14*f23*f3 + d2*f13*f24*f3 - d2*f15*f2*f32 + d2*f14*f22*f32 - d1*f13*f23*f32 + d2*f13*f23*f32 + d1*f12*f24*f32 - d2*f12*f24*f32 + d2*f14*f2*f33 + 2*d1*f13*f22*f33 - 2*d2*f13*f22*f33 - d1*f12*f23*f33 + d2*f12*f23*f33 - d1*f1*f24*f33 - d1*f13*f2*f34 - d1*f12*f22*f34 + 2*d1*f1*f23*f34 + d1*f12*f2*f35 - d1*f1*f22*f35 + 4*f12*f23*f32*v1 - 3*f1*f24*f32*v1 - 8*f12*f22*f33*v1 + 4*f1*f23*f33*v1 + f24*f33*v1 + 4*f12*f2*f34*v1 + f1*f22*f34*v1 - 2*f23*f34*v1 - 2*f1*f2*f35*v1 + f22*f35*v1 - f15*f32*v2 + 3*f14*f33*v2 - 3*f13*f34*v2 + f12*f35*v2 - f15*f22*v3 + 2*f14*f23*v3 - f13*f24*v3 + 2*f15*f2*f3*v3 - f14*f22*f3*v3 - 4*f13*f23*f3*v3 + 3*f12*f24*f3*v3 - 4*f14*f2*f32*v3 + 8*f13*f22*f32*v3 - 4*f12*f23*f32*v3) / ((f1 - f2)*(f1 - f2)*(f1 - f3)*(f1 - f3)*(f1 - f3)*(f3-f2)*(f3-f2)))
        delta1 = -((-(d2*f15*f22) + 2.*d2*f14*f23 - d2*f13*f24 - d2*f14*f22*f3 + 2.*d1*f13*f23*f3 + 2.*d2*f13*f23*f3 - 2*d1*f12*f24*f3 - d2*f12*f24*f3 + d2*f15*f32 - 3*d1*f13*f22*f32 - d2*f13*f22*f32 + 2*d1*f12*f23*f32 - 2*d2*f12*f23*f32 + d1*f1*f24*f32 + 2*d2*f1*f24*f32 - d2*f14*f33 + d1*f12*f22*f33 + 3*d2*f12*f22*f33 - 2*d1*f1*f23*f33 - 2*d2*f1*f23*f33 + d1*f24*f33 + d1*f13*f34 + d1*f1*f22*f34 - 2*d1*f23*f34 - d1*f12*f35 + d1*f22*f35 - 8*f12*f23*f3*v1 + 6*f1*f24*f3*v1 + 12*f12*f22*f32*v1 - 8*f1*f23*f32*v1 - 4*f12*f34*v1 + 2*f1*f35*v1 + 2*f15*f3*v2 - 4*f14*f32*v2 + 4*f12*f34*v2 - 2*f1*f35*v2 - 2*f15*f3*v3 + 8*f12*f23*f3*v3 - 6*f1*f24*f3*v3 + 4*f14*f32*v3 - 12*f12*f22*f32*v3 + 8*f1*f23*f32*v3) / ((f1 - f2)*(f1 - f2)*(f1 - f3)*(f1 - f3)*(f1 - f3)*(f3 - f2)*(f3 - f2)))
        delta2 = -((d2*f15*f2 - d1*f13*f23 - 3*d2*f13*f23 + d1*f12*f24 + 2.*d2*f12*f24 - d2*f15*f3 + d2*f14*f2*f3 - d1*f12*f23*f3 + d2*f12*f23*f3 + d1*f1*f24*f3 - d2*f1*f24*f3 - d2*f14*f32 + 3*d1*f13*f2*f32 + d2*f13*f2*f32 - d1*f1*f23*f32 + d2*f1*f23*f32 - 2*d1*f24*f32 - d2*f24*f32 - 2*d1*f13*f33 + 2*d2*f13*f33 - d1*f12*f2*f33 - 3*d2*f12*f2*f33 + 3*d1*f23*f33 + d2*f23*f33 + d1*f12*f34 - d1*f1*f2*f34 + d1*f1*f35 - d1*f2*f35 + 4*f12*f23*v1 - 3*f1*f24*v1 + 4*f1*f23*f3*v1 - 3*f24*f3*v1 - 12*f12*f2*f32*v1 + 4*f23*f32*v1 + 8*f12*f33*v1 - f1*f34*v1 - f35*v1 - f15*v2 - f14*f3*v2 + 8*f13*f32*v2 - 8*f12*f33*v2 + f1*f34*v2 + f35*v2 + f15*v3 - 4*f12*f23*v3 + 3*f1*f24*v3 + f14*f3*v3 - 4*f1*f23*f3*v3 + 3*f24*f3*v3 - 8*f13*f32*v3 + 12*f12*f2*f32*v3 - 4*f23*f32*v3) / ((f1 - f2)*(f1 - f2)*(f1 - f3)*(f1 - f3)*(f1 - f3)*(f3 - f2)*(f3 - f2)))
        delta3 = -((-2.*d2*f14*f2 + d1*f13*f22 + 3*d2*f13*f22 - d1*f1*f24 - d2*f1*f24 + 2*d2*f14*f3 - 2.*d1*f13*f2*f3 - 2*d2*f13*f2*f3 + d1*f12*f22*f3 - d2*f12*f22*f3 + d1*f24*f3 + d2*f24*f3 + d1*f13*f32 - d2*f13*f32 - 2*d1*f12*f2*f32 + 2*d2*f12*f2*f32 + d1*f1*f22*f32 - d2*f1*f22*f32 + d1*f12*f33 - d2*f12*f33 + 2*d1*f1*f2*f33 + 2*d2*f1*f2*f33 - 3*d1*f22*f33 - d2*f22*f33 - 2*d1*f1*f34 + 2*d1*f2*f34 - 4*f12*f22*v1 + 2*f24*v1 + 8*f12*f2*f3*v1 - 4*f1*f22*f3*v1 - 4*f12*f32*v1 + 8*f1*f2*f32*v1 - 4*f22*f32*v1 - 4*f1*f33*v1 + 2*f34*v1 + 2*f14*v2 - 4*f13*f3*v2 + 4*f1*f33*v2 - 2*f34*v2 - 2*f14*v3 + 4*f12*f22*v3 - 2*f24*v3 + 4*f13*f3*v3 - 8*f12*f2*f3*v3 + 4*f1*f22*f3*v3 + 4*f12*f32*v3 - 8*f1*f2*f32*v3 + 4*f22*f32*v3) / ((f1 - f2)*(f1 - f2)*(f1 - f3)*(f1 - f3)*(f1 - f3)*(f3 - f2)*(f3 - f2)))
        delta4 = -((d2*f13*f2 - d1*f12*f22 - 2*d2*f12*f22 + d1*f1*f23 + d2*f1*f23 - d2*f13*f3 + 2.*d1*f12*f2*f3 + d2*f12*f2*f3 - d1*f1*f22*f3 + d2*f1*f22*f3 - d1*f23*f3 - d2*f23*f3 - d1*f12*f32 + d2*f12*f32 - d1*f1*f2*f32 - 2*d2*f1*f2*f32 + 2*d1*f22*f32 + d2*f22*f32 + d1*f1*f33 - d1*f2*f33 + 3*f1*f22*v1 - 2*f23*v1 - 6*f1*f2*f3*v1 + 3*f22*f3*v1 + 3*f1*f32*v1 - f33*v1 - f13*v2 + 3*f12*f3*v2 - 3*f1*f32*v2 + f33*v2 + f13*v3 - 3*f1*f22*v3 + 2*f23*v3 - 3*f12*f3*v3 + 6*f1*f2*f3*v3 - 3*f22*f3*v3) / ((f1 - f2)*(f1 - f2)*(f1 - f3)*(f1 - f3)*(f1 - f3)*(f3 - f2)*(f3 - f2)))
        
        # Defined as in LALSimulation - LALSimIMRPhenomD.c line 332. Final units are correctly Hz^-1
        Overallamp = 2. * np.sqrt(5./(64.*np.pi)) * M * utils.GMsun_over_c2_Gpc * M * utils.GMsun_over_c3 / kwargs['dL']
        
        amplitudeIMR = np.where(fgrid < self.AMP_fJoin_INS, 1. + (fgrid**(2./3.))*Acoeffs['two_thirds'] + (fgrid**(4./3.)) * Acoeffs['four_thirds'] + (fgrid**(5./3.)) *  Acoeffs['five_thirds'] + (fgrid**(7./3.)) * Acoeffs['seven_thirds'] + (fgrid**(8./3.)) * Acoeffs['eight_thirds'] + fgrid * (Acoeffs['one'] + fgrid * Acoeffs['two'] + fgrid*fgrid * Acoeffs['three']), np.where(fgrid < fpeak, delta0 + fgrid*delta1 + fgrid*fgrid*(delta2 + fgrid*delta3 + fgrid*fgrid*delta4), np.where(fgrid < self.fcutPar,np.exp(-(fgrid - fring)*gamma2/(fdamp*gamma3))* (fdamp*gamma3*gamma1) / ((fgrid - fring)*(fgrid - fring) + fdamp*gamma3*fdamp*gamma3), 0.)))
        
        return Overallamp*amp0*(fgrid**(-7./6.))*amplitudeIMR
        
    def _finalspin(self, eta, chi1, chi2):
        """
        Compute the spin of the final object, as in LALSimIMRPhenomD_internals.c line 161 and 142, which is taken from `arXiv:1508.07250 <https://arxiv.org/abs/1508.07250>`_ eq. (3.6).
        
        :param cupy.ndarray or float eta: Symmetric mass ratio of the objects.
        :param cupy.ndarray or float chi1: Spin of the primary object.
        :param cupy.ndarray or float chi2: Spin of the secondary object.
        :return: The spin of the final object.
        :rtype: cupy.ndarray or float
        
        """
        Seta = np.sqrt(1.0 - 4.0*eta)
        m1 = 0.5 * (1.0 + Seta)
        m2 = 0.5 * (1.0 - Seta)
        s = (m1*m1 * chi1 + m2*m2 * chi2)
        
        af1 = eta*(3.4641016151377544 - 4.399247300629289*eta + 9.397292189321194*eta*eta - 13.180949901606242*eta*eta*eta)
        af2 = eta*(s*((1.0/eta - 0.0850917821418767 - 5.837029316602263*eta) + (0.1014665242971878 - 2.0967746996832157*eta)*s))
        af3 = eta*(s*((-1.3546806617824356 + 4.108962025369336*eta)*s*s + (-0.8676969352555539 + 2.064046835273906*eta)*s*s*s))
        return af1 + af2 + af3
        
    def _radiatednrg(self, eta, chi1, chi2):
        """
        Compute the total radiated energy, as in `arXiv:1508.07250 <https://arxiv.org/abs/1508.07250>`_ eq. (3.7) and (3.8).
        
        :param cupy.ndarray or float eta: Symmetric mass ratio of the objects.
        :param cupy.ndarray or float chi1: Spin of the primary object.
        :param cupy.ndarray or float chi2: Spin of the secondary object.
        :return: Total energy radiated by the system.
        :rtype: cupy.ndarray or float
        
        """
        Seta = np.sqrt(1.0 - 4.0*eta)
        m1 = 0.5 * (1.0 + Seta)
        m2 = 0.5 * (1.0 - Seta)
        s = (m1*m1 * chi1 + m2*m2 * chi2) / (m1*m1 + m2*m2)
        
        EradNS = eta * (0.055974469826360077 + 0.5809510763115132 * eta - 0.9606726679372312 * eta*eta + 3.352411249771192 * eta*eta*eta)
        
        return (EradNS * (1. + (-0.0030302335878845507 - 2.0066110851351073 * eta + 7.7050567802399215 * eta*eta) * s)) / (1. + (-0.6714403054720589 - 1.4756929437702908 * eta + 7.304676214885011 * eta*eta) * s)
    
    def tau_star(self, f, **kwargs):
        """
        Compute the time to coalescence (in seconds) as a function of frequency (in :math:`\\rm Hz`), given the events parameters.
        
        We use the expression in `arXiv:0907.0700 <https://arxiv.org/abs/0907.0700>`_ eq. (3.8b).
        
        :param cupy.ndarray f: Frequency grid on which the time to coalescence will be computed, in :math:`\\rm Hz`.
        :param dict(cupy.ndarray, cupy.ndarray, ...) kwargs: Dictionary with arrays containing the parameters of the events to compute the time to coalescence of, as in :py:data:`events`.
        :return: time to coalescence for the chosen events evaluated on the frequency grid, in seconds.
        :rtype: cupy.ndarray
        
        """
        utils.check_evparams(kwargs, checktidal=self.is_tidal)
        # For complex waveforms we use the expression in arXiv:0907.0700 eq. (3.8b)
        Mtot_sec = kwargs['Mc']*utils.GMsun_over_c3/(kwargs['eta']**(3./5.))
        v = (np.pi*Mtot_sec*f)**(1./3.)
        eta = kwargs['eta']
        eta2 = eta*eta
        
        OverallFac = 5./256 * Mtot_sec/(eta*(v**8.))
        
        t05 = 1. + (743./252. + 11./3.*eta)*(v*v) - 32./5.*np.pi*(v*v*v) + (3058673./508032. + 5429./504.*eta + 617./72.*eta2)*(v**4) - (7729./252. - 13./3.*eta)*np.pi*(v**5)
        t6  = (-10052469856691./23471078400. + 128./3.*np.pi*np.pi + 6848./105.*np.euler_gamma + (3147553127./3048192. - 451./12.*np.pi*np.pi)*eta - 15211./1728.*eta2 + 25565./1296.*eta2*eta + 3424./105.*np.log(16.*v*v))*(v**6)
        t7  = (- 15419335./127008. - 75703./756.*eta + 14809./378.*eta2)*np.pi*(v**7)
        
        return OverallFac*(t05 + t6 + t7)
    
    def fcut(self, **kwargs):
        """
        Compute the cut frequency of the waveform as a function of the events parameters, in :math:`\\rm Hz`.
        
        :param dict(cupy.ndarray, cupy.ndarray, ...) kwargs: Dictionary with arrays containing the parameters of the events to compute the cut frequency of, as in :py:data:`events`.
        :return: Cut frequency of the waveform for the chosen events, in :math:`\\rm Hz`.
        :rtype: cupy.ndarray
        
        """
        utils.check_evparams(kwargs, checktidal=self.is_tidal)
        return self.fcutPar/(kwargs['Mc']*utils.GMsun_over_c3/(kwargs['eta']**(3./5.)))
  
