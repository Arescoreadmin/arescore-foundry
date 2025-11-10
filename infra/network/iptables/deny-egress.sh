#!/usr/bin/env bash
#
# Harden container or host networking by dropping all outbound traffic
# except for an explicit allow-list. The script is idempotent and can
# be run on boot or as part of a container entrypoint.
#
# Environment variables:
#   ALLOWED_EGRESS_CIDRS   Space or comma separated list of CIDRs/hosts to allow.
#   ALLOWED_EGRESS_PORTS   Space separated list of destination ports to allow for the CIDRs.
#                          Defaults to 80 443.
#   ALLOW_DNS              When "true" (default) a minimal DNS rule is installed.
#
set -euo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  echo "[deny-egress] must be run as root" >&2
  exit 1
fi

readarray -td ',' raw_cidrs < <(echo "${ALLOWED_EGRESS_CIDRS:-}" | tr ' ' ','); raw_cidrs+=('')
allowed_cidrs=()
for entry in "${raw_cidrs[@]}"; do
  if [[ -n ${entry// /} ]]; then
    allowed_cidrs+=("${entry// /}")
  fi
done

read -ra allowed_ports <<<"${ALLOWED_EGRESS_PORTS:-80 443}"
allow_dns=${ALLOW_DNS:-true}

iptables -P OUTPUT DROP
iptables -F OUTPUT

iptables -A OUTPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

if [[ "${allow_dns,,}" == "true" ]]; then
  iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
fi

for cidr in "${allowed_cidrs[@]}"; do
  if [[ ${#allowed_ports[@]} -eq 0 ]]; then
    iptables -A OUTPUT -d "$cidr" -j ACCEPT
  else
    for port in "${allowed_ports[@]}"; do
      iptables -A OUTPUT -d "$cidr" -p tcp --dport "$port" -j ACCEPT
    done
  fi
done

echo "[deny-egress] outbound traffic restricted; allowed CIDRs: ${allowed_cidrs[*]:-(none)}"
