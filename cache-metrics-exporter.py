#!/usr/bin/env python3
"""
Cache Disk Metrics Exporter for Prometheus
Exposes cache disk usage metrics for TC-NGINX
"""

import os
import time
import subprocess
from prometheus_client import start_http_server, Gauge

# Create Prometheus metrics
cache_used_bytes = Gauge('nginx_cache_disk_used_bytes', 'Bytes used in cache', ['node', 'disk'])
cache_total_bytes = Gauge('nginx_cache_disk_total_bytes', 'Total cache capacity in bytes', ['node', 'disk'])
cache_object_count = Gauge('nginx_cache_object_count', 'Number of cached objects', ['node'])
cache_usage_percent = Gauge('nginx_cache_disk_usage_percent', 'Cache disk usage percentage', ['node', 'disk'])
cache_hits = Gauge('nginx_cache_hits_total', 'Total cache hits', ['node'])
cache_misses = Gauge('nginx_cache_misses_total', 'Total cache misses', ['node'])
cache_hit_ratio = Gauge('nginx_cache_hit_ratio', 'Cache hit ratio percentage', ['node'])
network_rx_bytes = Gauge('network_interface_rx_bytes', 'Network interface received bytes', ['interface'])
network_tx_bytes = Gauge('network_interface_tx_bytes', 'Network interface transmitted bytes', ['interface'])
network_rx_packets = Gauge('network_interface_rx_packets', 'Network interface received packets', ['interface'])
network_tx_packets = Gauge('network_interface_tx_packets', 'Network interface transmitted packets', ['interface'])

def get_docker_cache_stats():
    """Get cache statistics from Docker containers"""
    stats = {}
    
    # Dynamically detect running nginx-cache containers
    cmd = "docker ps --format '{{.Names}}' | grep 'tc-nginx-nginx-cache-[0-9]' | sort"
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    containers = result.stdout.strip().split('\n') if result.stdout.strip() else []
    
    for container in containers:
        # Extract node number from container name (e.g., tc-nginx-nginx-cache-1-1 -> 1)
        if 'nginx-cache-' in container:
            node_num = container.split('nginx-cache-')[1].split('-')[0]
            node_name = f"nginx-cache-{node_num}"
        
        try:
            # Get cache directory size - check which disks exist
            cache_size = 0
            object_count = 0
            
            # First check which disk directories exist in the container
            cmd = f"docker exec {container} ls -d /cache/disk* 2>/dev/null"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            available_disks = []
            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if '/cache/disk' in line:
                        disk_num = line.replace('/cache/disk', '')
                        if disk_num.isdigit():
                            available_disks.append(int(disk_num))
            
            # Use detected disks, or default to checking disks 1-4
            disks_to_check = available_disks if available_disks else [1, 2, 3, 4]
            
            for disk in disks_to_check:
                # Get size for this disk
                cmd = f"docker exec {container} du -sb /cache/disk{disk}"
                result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                if result.returncode == 0 and result.stdout.strip():
                    # Parse the output: "size<tab>path"
                    cache_size += int(result.stdout.strip().split()[0])
                
                # Get object count for this disk
                cmd = f"docker exec {container} find /cache/disk{disk} -type f | wc -l"
                result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                if result.returncode == 0:
                    object_count += int(result.stdout.strip())
            
            # Get cache hit/miss stats from logs (last 1000 lines)
            cmd = f"docker logs {container} --tail 1000 2>&1 | grep CacheStatus"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            hits = 0
            misses = 0
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.splitlines():
                    if 'CacheStatus=HIT' in line:
                        hits += 1
                    elif 'CacheStatus=MISS' in line:
                        misses += 1
                
            stats[node_name] = {
                'cache_size': cache_size,
                'object_count': object_count,
                'hits': hits,
                'misses': misses
            }
        except Exception as e:
            print(f"Error getting stats for {node_name}: {e}")
            stats[node_name] = {'cache_size': 0, 'object_count': 0, 'hits': 0, 'misses': 0}
    
    return stats

def get_disk_stats():
    """Get physical disk statistics"""
    disk_stats = {}
    
    # Map cache nodes to their disk mounts
    # Each cache node uses all 4 disks, but let's track physical disk usage
    disk_mounts = {
        'disk1': '/mnt/disk1',
        'disk2': '/mnt/disk2', 
        'disk3': '/mnt/disk3',
        'disk4': '/mnt/disk4'
    }
    
    for disk_name, mount_path in disk_mounts.items():
        try:
            # Get disk usage using df command
            cmd = f"df -B1 {mount_path} 2>/dev/null | tail -n1"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                if len(parts) >= 4:
                    total = int(parts[1])
                    used = int(parts[2])
                    available = int(parts[3])
                    percent = (used / total * 100) if total > 0 else 0
                    
                    disk_stats[disk_name] = {
                        'total': total,
                        'used': used,
                        'available': available,
                        'percent': percent
                    }
                else:
                    disk_stats[disk_name] = {'total': 0, 'used': 0, 'available': 0, 'percent': 0}
            else:
                disk_stats[disk_name] = {'total': 0, 'used': 0, 'available': 0, 'percent': 0}
                
        except Exception as e:
            print(f"Error getting disk stats for {disk_name}: {e}")
            disk_stats[disk_name] = {'total': 0, 'used': 0, 'available': 0, 'percent': 0}
    
    return disk_stats

def get_network_stats():
    """Get network interface statistics for cache containers"""
    net_stats = {}
    
    # Get stats for each cache node container
    for node in range(1, 5):
        node_name = f"nginx-cache-{node}"
        container = f"tc-nginx-nginx-cache-{node}-1"
        
        try:
            # Get container's network interface stats
            cmd = f"docker exec {container} cat /proc/net/dev | grep eth0"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            
            if result.returncode == 0 and result.stdout:
                # Parse the line: interface: rx_bytes rx_packets ... tx_bytes tx_packets ...
                line = result.stdout.strip()
                if ':' in line:
                    stats_part = line.split(':', 1)[1].strip()
                    parts = stats_part.split()
                    if len(parts) >= 9:
                        net_stats[node_name] = {
                            'rx_bytes': int(parts[0]),
                            'rx_packets': int(parts[1]),
                            'tx_bytes': int(parts[8]),
                            'tx_packets': int(parts[9])
                        }
                    else:
                        net_stats[node_name] = {'rx_bytes': 0, 'rx_packets': 0, 'tx_bytes': 0, 'tx_packets': 0}
                else:
                    net_stats[node_name] = {'rx_bytes': 0, 'rx_packets': 0, 'tx_bytes': 0, 'tx_packets': 0}
            else:
                net_stats[node_name] = {'rx_bytes': 0, 'rx_packets': 0, 'tx_bytes': 0, 'tx_packets': 0}
                
        except Exception as e:
            print(f"Error getting network stats for {node_name}: {e}")
            net_stats[node_name] = {'rx_bytes': 0, 'rx_packets': 0, 'tx_bytes': 0, 'tx_packets': 0}
    
    return net_stats

def update_metrics():
    """Update Prometheus metrics"""
    # Get container cache stats
    docker_stats = get_docker_cache_stats()
    
    total_cache_used = 0
    total_objects = 0
    total_hits = 0
    total_misses = 0
    
    # Clear metrics for all possible nodes first (1-4)
    for i in range(1, 5):
        node_name = f"nginx-cache-{i}"
        if node_name not in docker_stats:
            # Set metrics to 0 for non-existent nodes
            cache_object_count.labels(node=node_name).set(0)
            cache_used_bytes.labels(node=node_name, disk='cache').set(0)
            cache_total_bytes.labels(node=node_name, disk='cache').set(0)
            cache_usage_percent.labels(node=node_name, disk='cache').set(0)
            cache_hits.labels(node=node_name).set(0)
            cache_misses.labels(node=node_name).set(0)
            cache_hit_ratio.labels(node=node_name).set(0)
    
    # Update container metrics
    for node_name, stats in docker_stats.items():
        node_num = node_name.split('-')[-1]
        cache_object_count.labels(node=node_name).set(stats['object_count'])
        total_cache_used += stats['cache_size']
        total_objects += stats['object_count']
        total_hits += stats['hits']
        total_misses += stats['misses']
        
        # Report per-node cache usage (using container's /var/cache/nginx)
        # Each node has 10GB max cache configured in nginx
        cache_used_bytes.labels(node=node_name, disk='cache').set(stats['cache_size'])
        cache_total_bytes.labels(node=node_name, disk='cache').set(10 * 1024 * 1024 * 1024)  # 10GB per node
        cache_usage_percent.labels(node=node_name, disk='cache').set(
            (stats['cache_size'] / (10 * 1024 * 1024 * 1024) * 100) if stats['cache_size'] > 0 else 0
        )
        
        # Report hit/miss stats
        cache_hits.labels(node=node_name).set(stats['hits'])
        cache_misses.labels(node=node_name).set(stats['misses'])
        hit_ratio = (stats['hits'] / (stats['hits'] + stats['misses']) * 100) if (stats['hits'] + stats['misses']) > 0 else 0
        cache_hit_ratio.labels(node=node_name).set(hit_ratio)
    
    # Get actual physical disk stats
    disk_stats = get_disk_stats()
    total_physical_capacity = 0
    total_physical_used = 0
    
    for disk_name, stats in disk_stats.items():
        cache_used_bytes.labels(node='physical', disk=disk_name).set(stats['used'])
        cache_total_bytes.labels(node='physical', disk=disk_name).set(stats['total'])
        cache_usage_percent.labels(node='physical', disk=disk_name).set(stats['percent'])
        total_physical_capacity += stats['total']
        total_physical_used += stats['used']
    
    # Report aggregate totals using actual physical disk capacity
    # Use physical disk capacity for total, but container cache for used
    cache_used_bytes.labels(node='all', disk='total').set(total_cache_used)
    cache_total_bytes.labels(node='all', disk='total').set(total_physical_capacity)
    cache_usage_percent.labels(node='all', disk='total').set(
        (total_cache_used / total_physical_capacity * 100) if total_physical_capacity > 0 else 0
    )
    
    # Report aggregate hit/miss stats
    cache_hits.labels(node='all').set(total_hits)
    cache_misses.labels(node='all').set(total_misses)
    total_hit_ratio = (total_hits / (total_hits + total_misses) * 100) if (total_hits + total_misses) > 0 else 0
    cache_hit_ratio.labels(node='all').set(total_hit_ratio)
    
    # Get and update network stats
    net_stats = get_network_stats()
    for iface, stats in net_stats.items():
        network_rx_bytes.labels(interface=iface).set(stats['rx_bytes'])
        network_tx_bytes.labels(interface=iface).set(stats['tx_bytes'])
        network_rx_packets.labels(interface=iface).set(stats['rx_packets'])
        network_tx_packets.labels(interface=iface).set(stats['tx_packets'])

def main():
    # Start Prometheus metrics server on port 9199
    start_http_server(9199)
    print("Cache metrics exporter started on port 9199")
    
    # Update metrics every 30 seconds
    while True:
        try:
            update_metrics()
            print(f"Metrics updated at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"Error updating metrics: {e}")
        
        time.sleep(30)

if __name__ == '__main__':
    main()