# Grafana Insights for Render (Neon datasource via PRA_PG_*).
# Local Ops stays on docker-compose :3002.
FROM grafana/grafana:10.4.19

USER root
COPY grafana/provisioning /etc/grafana/provisioning
COPY grafana/dashboards /etc/grafana/dashboards
COPY grafana/docker-entrypoint.sh /usr/local/bin/pra-grafana-entrypoint.sh
RUN chmod +x /usr/local/bin/pra-grafana-entrypoint.sh
USER 472

EXPOSE 3000
ENTRYPOINT ["/usr/local/bin/pra-grafana-entrypoint.sh"]
