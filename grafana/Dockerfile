# Grafana Insights for Render (Neon datasource via PRA_PG_*).
# Build context = grafana/ (see render.yaml dockerContext).
# Local Ops stays on docker-compose :3002.
FROM grafana/grafana:10.4.19

USER root
COPY provisioning /etc/grafana/provisioning
COPY dashboards /etc/grafana/dashboards
COPY docker-entrypoint.sh /usr/local/bin/pra-grafana-entrypoint.sh
RUN chmod +x /usr/local/bin/pra-grafana-entrypoint.sh
USER 472

EXPOSE 3000
ENTRYPOINT ["/usr/local/bin/pra-grafana-entrypoint.sh"]
