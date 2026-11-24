FROM jxxghp/moviepilot-v3:3.2.0
COPY --chmod=0444 provider.py /provider.py
COPY --chmod=0444 quality.py /quality.py
USER 65532:65532
ENTRYPOINT ["python", "/provider.py"]
