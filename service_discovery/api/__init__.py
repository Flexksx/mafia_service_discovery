from fastapi import APIRouter, Response
from service_discovery.service_registration.health_monitor import health_monitor
from service_discovery.service_registration.registry import service_registry
from service_discovery.logger_config import ServiceDiscoveryLogger

logger = ServiceDiscoveryLogger.get_logger(__name__)

from service_discovery.api.routes import router as discovery_router

# Main API router that includes all sub-routers
api_router = APIRouter()

# Include discovery routes with prefix
api_router.include_router(
    discovery_router, prefix="/v1/discovery", tags=["Service Discovery"]
)

# Add metrics endpoint directly to main router (no prefix)
@api_router.get("/metrics")
async def get_prometheus_metrics():
    """Prometheus metrics endpoint for monitoring service discovery"""
    try:
        stats = health_monitor.get_monitoring_stats()
        alert_states = health_monitor.get_alert_states()
        all_services = await service_registry.get_all_services()
        
        # Calculate metrics
        total_services = sum(len(instances) for instances in all_services.values())
        total_healthy_services = sum(
            len([inst for inst in instances if inst.status.value == "healthy"])
            for instances in all_services.values()
        )
        total_unhealthy_services = sum(
            len([inst for inst in instances if inst.status.value == "unhealthy"])
            for instances in all_services.values()
        )
        
        # Calculate success rate
        total_checks = stats["total_checks"]
        success_rate = (stats["successful_checks"] / total_checks * 100) if total_checks > 0 else 0
        
        # Build Prometheus metrics format
        metrics = []
        
        # Service Discovery Metrics
        metrics.append("# HELP service_discovery_registered_services_total Total number of registered services")
        metrics.append("# TYPE service_discovery_registered_services_total counter")
        metrics.append(f"service_discovery_registered_services_total {total_services}")
        
        metrics.append("# HELP service_discovery_healthy_services_total Total number of healthy services")
        metrics.append("# TYPE service_discovery_healthy_services_total counter")
        metrics.append(f"service_discovery_healthy_services_total {total_healthy_services}")
        
        metrics.append("# HELP service_discovery_unhealthy_services_total Total number of unhealthy services")
        metrics.append("# TYPE service_discovery_unhealthy_services_total counter")
        metrics.append(f"service_discovery_unhealthy_services_total {total_unhealthy_services}")
        
        # Health Monitoring Metrics
        metrics.append("# HELP service_discovery_health_checks_total Total number of health checks performed")
        metrics.append("# TYPE service_discovery_health_checks_total counter")
        metrics.append(f"service_discovery_health_checks_total {total_checks}")
        
        metrics.append("# HELP service_discovery_health_checks_successful_total Total number of successful health checks")
        metrics.append("# TYPE service_discovery_health_checks_successful_total counter")
        metrics.append(f"service_discovery_health_checks_successful_total {stats['successful_checks']}")
        
        metrics.append("# HELP service_discovery_health_checks_failed_total Total number of failed health checks")
        metrics.append("# TYPE service_discovery_health_checks_failed_total counter")
        metrics.append(f"service_discovery_health_checks_failed_total {stats['failed_checks']}")
        
        metrics.append("# HELP service_discovery_health_check_success_rate_percent Health check success rate percentage")
        metrics.append("# TYPE service_discovery_health_check_success_rate_percent gauge")
        metrics.append(f"service_discovery_health_check_success_rate_percent {success_rate:.2f}")
        
        # Alert Metrics
        metrics.append("# HELP service_discovery_alerts_warning_total Total number of warning alerts")
        metrics.append("# TYPE service_discovery_alerts_warning_total counter")
        metrics.append(f"service_discovery_alerts_warning_total {stats['warning_alerts']}")
        
        metrics.append("# HELP service_discovery_alerts_critical_total Total number of critical alerts")
        metrics.append("# TYPE service_discovery_alerts_critical_total counter")
        metrics.append(f"service_discovery_alerts_critical_total {stats['critical_alerts']}")
        
        metrics.append("# HELP service_discovery_alerts_emergency_total Total number of emergency alerts")
        metrics.append("# TYPE service_discovery_alerts_emergency_total counter")
        metrics.append(f"service_discovery_alerts_emergency_total {stats['emergency_alerts']}")
        
        # Service-specific metrics
        for service_name, instances in all_services.items():
            healthy_count = len([inst for inst in instances if inst.status.value == "healthy"])
            unhealthy_count = len([inst for inst in instances if inst.status.value == "unhealthy"])
            
            metrics.append(f"service_discovery_service_instances_total{{service=\"{service_name}\"}} {len(instances)}")
            metrics.append(f"service_discovery_service_healthy_instances_total{{service=\"{service_name}\"}} {healthy_count}")
            metrics.append(f"service_discovery_service_unhealthy_instances_total{{service=\"{service_name}\"}} {unhealthy_count}")
            
            # Load metrics per service
            for instance in instances:
                metrics.append(f"service_discovery_service_load_percentage{{service=\"{service_name}\",instance=\"{instance.instance_id}\",host=\"{instance.host}\"}} {instance.load_percentage}")
        
        # Alert states metrics
        for service_key, alert_state in alert_states.items():
            service_name, instance_id = service_key.split(":", 1)
            metrics.append(f"service_discovery_alert_count_total{{service=\"{service_name}\",instance=\"{instance_id}\"}} {alert_state.alert_count}")
        
        # Monitoring status
        monitoring_enabled = 1 if health_monitor.is_monitoring_enabled() else 0
        metrics.append("# HELP service_discovery_monitoring_enabled Whether monitoring is enabled")
        metrics.append("# TYPE service_discovery_monitoring_enabled gauge")
        metrics.append(f"service_discovery_monitoring_enabled {monitoring_enabled}")
        
        # Join all metrics
        metrics_text = "\n".join(metrics)
        
        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}")
        return Response(
            content=f"# Error generating metrics: {str(e)}\n",
            media_type="text/plain; version=0.0.4; charset=utf-8",
            status_code=500
        )
