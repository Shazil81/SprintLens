from django.db import migrations


def backfill(apps, schema_editor):
    AuditEvent = apps.get_model('workspace', 'AuditEvent')
    Project = apps.get_model('workspace', 'Project')
    for project in Project.objects.all().iterator():
        AuditEvent.objects.filter(project_id=project.pk, organization__isnull=True).update(organization_id=project.organization_id)


class Migration(migrations.Migration):
    dependencies = [('workspace', '0003_auditevent_organization_project_version_and_more')]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
