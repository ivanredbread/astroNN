from astroNN.models.NeuralNetMaster import NeuralNetMaster
import os
import time
import keras.backend as K

K.set_learning_phase(1)

class ASPCAP_plots(NeuralNetMaster):

    def __init__(self):
        super(ASPCAP_plots, self).__init__()

    def aspcap_residue_plot(self, test_predictions, test_labels, test_pred_error):
        import pylab as plt
        from astroNN.shared.nn_tools import target_name_conversion
        import numpy as np
        import seaborn as sns

        print("Start plotting residues")

        resid = test_predictions - test_labels

        # Some plotting variables for asthetics
        plt.rcParams['axes.facecolor'] = 'white'
        sns.set_style("ticks")
        plt.rcParams['axes.grid'] = True
        plt.rcParams['grid.color'] = 'gray'
        plt.rcParams['grid.alpha'] = '0.4'

        x_lab = 'ASPCAP'
        y_lab = 'astroNN'
        fullname = self.targetname

        aspcap_residue_path = os.path.join(self.fullfilepath, 'ASPCAP_residue')

        if not os.path.exists(aspcap_residue_path):
            os.makedirs(aspcap_residue_path)

        magic_number = -9999.

        std_labels = np.zeros(test_labels.shape[1])

        for i in range(test_labels.shape[1]):
            not9999_index = np.where(test_labels[:, i] != magic_number)
            std_labels[i] = np.std((test_labels[:, i])[not9999_index], axis=0)

        for i in range(self.labels_shape):
            plt.figure(figsize=(15, 11), dpi=200)
            plt.axhline(0, ls='--', c='k', lw=2)
            not9999 = np.where(test_labels[:, i] != -9999.)[0]
            plt.errorbar((test_labels[:, i])[not9999], (resid[:, i])[not9999], yerr=(test_pred_error[:, i])[not9999],
                         markersize=2, fmt='o', ecolor='g', capthick=2, elinewidth=0.5)

            plt.xlabel('ASPCAP ' + target_name_conversion(fullname[i]), fontsize=25)
            plt.ylabel('$\Delta$ ' + target_name_conversion(fullname[i]) + '\n(' + y_lab + ' - ' + x_lab + ')',
                       fontsize=25)
            plt.tick_params(labelsize=20, width=1, length=10)
            if self.labels_shape == 1:
                plt.xlim([np.min((test_labels[:])[not9999]), np.max((test_labels[:])[not9999])])
            else:
                plt.xlim([np.min((test_labels[:, i])[not9999]), np.max((test_labels[:, i])[not9999])])
            ranges = (np.max((test_labels[:, i])[not9999]) - np.min((test_labels[:, i])[not9999])) / 2
            plt.ylim([-ranges, ranges])
            bbox_props = dict(boxstyle="square,pad=0.3", fc="w", ec="k", lw=2)
            bias = np.median((resid[:, i])[not9999])
            scatter = np.std((resid[:, i])[not9999])
            plt.figtext(0.6, 0.75,
                        '$\widetilde{m}$=' + '{0:.3f}'.format(bias) + ' $\widetilde{s}$=' + '{0:.3f}'.format(
                            scatter / float(std_labels[i])) + ' s=' + '{0:.3f}'.format(scatter), size=25, bbox=bbox_props)
            plt.tight_layout()
            plt.savefig(aspcap_residue_path + '/{}_test.png'.format(fullname[i]))
            plt.close('all')
            plt.clf()

        print("Finished plotting residues")

    def jacobian(self, x=None, plotting=True):
        """
        NAME: cal_jacobian
        PURPOSE: calculate jacobian
        INPUT:
        OUTPUT:
        HISTORY:
            2017-Nov-20 Henry Leung
        """
        import pylab as plt
        import numpy as np
        import seaborn as sns
        import matplotlib.ticker as ticker
        from astroNN.apogee.chips import wavelength_solution, chips_split
        from astroNN.shared.nn_tools import aspcap_windows_url_correction
        from urllib.request import urlopen
        import pandas as pd

        if x is None:
            raise ValueError('Please provide data to calculate the jacobian')

        dr = 14

        x = np.atleast_3d(x)
        # enforce float16 because the precision doesnt really matter
        input_tens = self.keras_model.layers[0].input
        jacobian = np.empty((self.labels_shape, x.shape[0], x.shape[1]), dtype=np.float16)
        start_time = time.time()

        with K.get_session() as sess:
            K.set_learning_phase(0)
            for counter, j in enumerate(range(self.labels_shape)):
                print('Completed {} of {} output, {:.03f} seconds elapsed'.format(counter, self.labels_shape,
                                                                                  time.time() - start_time))
                grad = self.keras_model.layers[-1].output[0, j]
                for i in range(x.shape[0]):
                    jacobian[j, i:i + 1, :] = (np.asarray(sess.run(K.tf.gradients(grad, input_tens),
                                                                   feed_dict={input_tens: x[i:i + 1]})))[:, :, 0].T

            # Some plotting variables for asthetics
            plt.rcParams['axes.facecolor'] = 'white'
            sns.set_style("ticks")
            plt.rcParams['axes.grid'] = False
            plt.rcParams['grid.color'] = 'gray'
            plt.rcParams['grid.alpha'] = '0.4'
            path = os.path.join(self.fullfilepath, 'jacobian')
            if not os.path.exists(path):
                os.makedirs(path)

            fullname = self.targetname
            lambda_blue, lambda_green, lambda_red = wavelength_solution(dr=dr)

            for j in range(self.labels_shape):
                fig = plt.figure(figsize=(45, 30), dpi=150)
                scale = np.max(np.abs((jacobian[j, :])))
                scale_2 = np.min((jacobian[j, :]))
                blue, green, red = chips_split(jacobian[j, :], dr=dr)
                ax1 = fig.add_subplot(311)
                fig.suptitle('{}, Average of {} Stars'.format(fullname[j], x.shape[0]), fontsize=50)
                ax1.set_ylabel(r'$\partial$' + fullname[j], fontsize=40)
                ax1.set_ylim(scale_2, scale)
                ax1.plot(lambda_blue, blue, linewidth=0.9, label='astroNN')
                ax2 = fig.add_subplot(312)
                ax2.set_ylabel(r'$\partial$' + fullname[j], fontsize=40)
                ax2.set_ylim(scale_2, scale)
                ax2.plot(lambda_green, green, linewidth=0.9, label='astroNN')
                ax3 = fig.add_subplot(313)
                ax3.set_ylim(scale_2, scale)
                ax3.set_ylabel(r'$\partial$' + fullname[j], fontsize=40)
                ax3.plot(lambda_red, red, linewidth=0.9, label='astroNN')
                ax3.set_xlabel(r'Wavelength (Angstrom)', fontsize=40)

                ax1.axhline(0, ls='--', c='k', lw=2)
                ax2.axhline(0, ls='--', c='k', lw=2)
                ax3.axhline(0, ls='--', c='k', lw=2)

                try:
                    if dr == 14:
                        url = "https://svn.sdss.org/public/repo/apogee/idlwrap/trunk/lib/l31c/{}.mask".format(
                            aspcap_windows_url_correction(self.targetname[j]))
                    else:
                        raise ValueError('Only support DR14')
                    df = np.array(pd.read_csv(urlopen(url), header=None, sep='\t'))
                    print(url)
                    aspcap_windows = df * scale
                    aspcap_blue, aspcap_green, aspcap_red = chips_split(aspcap_windows, dr=dr)
                    ax1.plot(lambda_blue, aspcap_blue, linewidth=0.9, label='ASPCAP windows')
                    ax2.plot(lambda_green, aspcap_green, linewidth=0.9, label='ASPCAP windows')
                    ax3.plot(lambda_red, aspcap_red, linewidth=0.9, label='ASPCAP windows')
                except:
                    print('No ASPCAP windows data for {}'.format(aspcap_windows_url_correction(self.targetname[j])))
                tick_spacing = 50
                ax1.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing))
                ax2.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing / 1.5))
                ax3.xaxis.set_major_locator(ticker.MultipleLocator(tick_spacing / 1.7))
                ax1.minorticks_on()
                ax2.minorticks_on()
                ax3.minorticks_on()

                ax1.tick_params(labelsize=30, width=2, length=20, which='major')
                ax1.tick_params(width=2, length=10, which='minor')
                ax2.tick_params(labelsize=30, width=2, length=20, which='major')
                ax2.tick_params(width=2, length=10, which='minor')
                ax3.tick_params(labelsize=30, width=2, length=20, which='major')
                ax3.tick_params(width=2, length=10, which='minor')
                ax1.legend(loc='best', fontsize=40)
                plt.tight_layout()
                plt.subplots_adjust(left=0.05)
                plt.savefig(path + '/{}_jacobian.png'.format(self.targetname[j]))
                plt.close('all')
                plt.clf()

        return jacobian