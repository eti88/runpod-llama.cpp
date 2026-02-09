#!/bin/bash
set -e

# Setup SSH if PUBLIC_KEY is provided
if [ -n "${PUBLIC_KEY}" ]; then
    echo "Setting up SSH with provided public key..."
    mkdir -p /root/.ssh
    chmod 700 /root/.ssh
    echo "${PUBLIC_KEY}" > /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
fi

# Start SSH service
if [ -f /usr/sbin/sshd ]; then
    echo "Starting SSH service..."
    service ssh start || /usr/sbin/sshd
fi

# Start supervisord
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf
