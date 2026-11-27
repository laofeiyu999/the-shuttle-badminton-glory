# 音轨分析：在每个触球时刻前后量短时能量、高频(>4 kHz)能量、谱质心；用于判断不同档位是否有不同击球音
# 先生成输入: ffmpeg -v fatal -y -i src/tb1.mp4 -vn -ac 1 -ar 48000 -f s16le data/C_tb1_audio.raw （约 5 MB，用完可删）
import numpy as np
a = np.fromfile('data/C_tb1_audio.raw', dtype=np.int16).astype(float) / 32768; sr = 48000
N, hop = 1024, 240
win = np.hanning(N)
nfr = (len(a) - N) // hop
S = np.abs(np.fft.rfft(np.stack([a[i * hop:i * hop + N] * win for i in range(nfr)]), axis=1))
fq = np.fft.rfftfreq(N, 1 / sr); t = (np.arange(nfr) * hop + N / 2) / sr
E_all = (S ** 2).sum(1); hf = (S[:, fq > 4000] ** 2).sum(1); lf = (S[:, fq < 500] ** 2).sum(1)
flux = np.maximum(S[1:] - S[:-1], 0).sum(1); flux = np.r_[0, flux]
med = np.median(flux)
hits = [('O0', 1.70, 'norm'), ('P0b', 2.60, 'perf'), ('S1', 14.22, 'serve'), ('P1', 15.02, 'perf'), ('O1', 15.99, 'perf'), ('P2', 16.47, 'perf'), ('O2', 17.45, 'norm'), ('P3', 18.35, 'norm'),
        ('O3', 19.33, 'norm'), ('P4', 20.43, 'perf'), ('O4', 21.04, 'norm'), ('P5', 22.15, 'perf'), ('O5', 22.81, 'smash'), ('P6', 23.13, 'bad'), ('O6', 24.48, 'norm'), ('P7', 25.56, 'perf'),
        ('S2', 33.90, 'serve'), ('P1p', 34.64, 'perf'), ('O1p', 35.58, 'norm'), ('P2p', 36.66, 'norm'), ('O2p', 37.82, 'norm'), ('P3p', 39.10, 'norm'), ('O3p', 40.36, 'smash'), ('P4p', 40.62, 'perf'),
        ('O4p', 41.74, 'perf'), ('P5p', 42.32, 'perf'), ('O5p', 43.16, 'norm'), ('P6p', 44.05, 'perf')]
print('name kind  t_hit  onset_t  dt   flux/med  E_dB  HF_dB  centroid_Hz  dur_ms(>-10dB)')
for name, th, kind in hits:
    sel = np.nonzero((t > th - 0.12) & (t < th + 0.25))[0]
    k = sel[np.argmax(flux[sel])]
    seg = slice(k, k + 12)  # 60 ms after onset
    Sm = S[seg].mean(0)
    cen = (Sm ** 2 * fq).sum() / (Sm ** 2).sum()
    e = E_all[k:k + 100]; pk = e[:20].max(); dur = np.argmax(e[np.argmax(e[:20]):] < pk * 0.1) * hop / sr * 1000
    base = np.median(E_all[max(k - 100, 0):k - 10])
    print(f'{name:5s} {kind:5s} {th:6.2f} {t[k]:7.3f} {t[k]-th:+.3f} {flux[k]/med:7.1f} {10*np.log10(E_all[seg].mean()/base):6.1f} {10*np.log10(hf[seg].mean()/np.median(hf)):6.1f} {cen:8.0f} {dur:6.0f}')
# 全片最强的 40 个 onset（看是否有未对应击球的提示音）
pk = [i for i in range(2, nfr - 2) if flux[i] == flux[max(i - 20, 0):i + 20].max() and flux[i] > 6 * med]
print('strong onsets:', ' '.join(f'{t[i]:.2f}({flux[i]/med:.0f})' for i in pk))
