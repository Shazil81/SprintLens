import uuid
from django.conf import settings
from django.db import models


class Organization(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)


class Membership(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'Admin'
        MANAGER = 'Manager'
        DEVELOPER = 'Developer'

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    role = models.CharField(max_length=12, choices=Role.choices)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['organization', 'user'], name='unique_organization_member')]


class Project(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=12)
    description = models.TextField(blank=True)
    due = models.DateField()
    color = models.CharField(max_length=12, choices=[(v, v) for v in ['purple', 'orange', 'green', 'blue']], default='blue')
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['organization', 'code'], name='unique_project_code')]


class ProjectMembership(models.Model):
    is_reviewer = models.BooleanField(default=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='memberships')
    membership = models.ForeignKey(Membership, on_delete=models.CASCADE, related_name='projects')

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.project.organization_id != self.membership.organization_id:
            raise ValidationError('Project and member must belong to the same organization.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['project', 'membership'], name='unique_project_member')]


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = 'To do'
        IN_PROGRESS = 'In progress'
        IN_REVIEW = 'In review'
        BLOCKED = 'Blocked'
        DONE = 'Done'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name='tasks')
    title = models.CharField(max_length=140)
    assignee = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name='tasks')
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.TODO)
    priority = models.CharField(max_length=8, choices=[(v, v) for v in ['Low', 'Medium', 'High']], default='Medium')
    complexity = models.CharField(max_length=16, choices=[(v, v) for v in ['Unestimated', 'Small', 'Medium', 'Large']], default='Unestimated')
    complexity_context = models.TextField(blank=True)
    due = models.DateField()
    acceptance_criteria = models.TextField(blank=True)
    milestone = models.ForeignKey('Milestone', on_delete=models.PROTECT, null=True, blank=True, related_name='tasks')
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', 'id']
        indexes = [models.Index(fields=['project', 'status']), models.Index(fields=['assignee', 'due'])]


class AuditEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, null=True, blank=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    task = models.ForeignKey(Task, on_delete=models.PROTECT, null=True, blank=True)
    action = models.CharField(max_length=30)
    text = models.TextField()
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    request_id = models.UUIDField(default=uuid.uuid4)
    at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Existing task writers automatically attach the organization; never store credentials here.
        if self.project_id and self.organization_id is None:
            self.organization_id = self.project.organization_id
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['-at', 'id']


class WorkUpdate(models.Model):
    """An append-only progress note or manager feedback item on a task."""
    class Kind(models.TextChoices):
        UPDATE = 'Update'
        FEEDBACK = 'Feedback'

    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name='work_updates')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.UPDATE)
    body = models.TextField()
    evidence_url = models.URLField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


class Blocker(models.Model):
    """Track the reason, accountable owner, and resolution of blocked work."""
    task = models.ForeignKey(Task, on_delete=models.PROTECT, related_name='blockers')
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reported_blockers')
    owner = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name='owned_blockers')
    reason = models.TextField()
    opened_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name='resolved_blockers')
    resolution = models.TextField(blank=True)

    class Meta:
        ordering = ['-opened_at', '-id']


class Milestone(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    title = models.CharField(max_length=140)
    kind = models.CharField(max_length=12, choices=[('Milestone', 'Milestone'), ('Sprint', 'Sprint')], default='Milestone')
    start = models.DateField()
    due = models.DateField()
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['due', 'id']


class TaskDependency(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='dependencies')
    depends_on = models.ForeignKey(Task, on_delete=models.PROTECT, related_name='dependents')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['task', 'depends_on'], name='unique_task_dependency'),
                       models.CheckConstraint(condition=~models.Q(task=models.F('depends_on')), name='no_self_dependency')]


class PerformanceReview(models.Model):
    """A private, structured review; published text is immutable."""
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    subject = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name='received_reviews')
    reviewer = models.ForeignKey(Membership, on_delete=models.PROTECT, related_name='written_reviews')
    cycle = models.CharField(max_length=120)
    period_start = models.DateField()
    period_end = models.DateField()
    strengths = models.TextField()
    improvements = models.TextField()
    collaboration = models.TextField()
    delivery_context = models.TextField()
    status = models.CharField(max_length=16, default='Draft', choices=[(v, v) for v in ['Draft', 'Published', 'Responded']])
    version = models.PositiveIntegerField(default=1)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ReviewResponse(models.Model):
    review = models.ForeignKey(PerformanceReview, on_delete=models.PROTECT, related_name='responses')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']


class GrowthGoal(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    owner = models.ForeignKey(Membership, on_delete=models.PROTECT)
    title = models.CharField(max_length=140)
    skill = models.CharField(max_length=100)
    target_date = models.DateField()
    status = models.CharField(max_length=16, default='Planned', choices=[(v, v) for v in ['Planned', 'In progress', 'Achieved']])
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['target_date', 'id']


class GoalEntry(models.Model):
    goal = models.ForeignKey(GrowthGoal, on_delete=models.PROTECT, related_name='entries')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=12, choices=[('Progress', 'Progress'), ('Feedback', 'Feedback')])
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']


class GitHubConnection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    repository = models.CharField(max_length=200, unique=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']


class GitHubDelivery(models.Model):
    connection = models.ForeignKey(GitHubConnection, on_delete=models.CASCADE)
    delivery_id = models.CharField(max_length=100)
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['connection', 'delivery_id'], name='unique_github_delivery')]


class GitHubActivity(models.Model):
    connection = models.ForeignKey(GitHubConnection, on_delete=models.PROTECT)
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    event = models.CharField(max_length=30)
    title = models.CharField(max_length=300)
    actor = models.CharField(max_length=100)
    url = models.URLField(max_length=1000, blank=True)
    external_id = models.CharField(max_length=100)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-at', '-id']


class Notification(models.Model):
    recipient = models.ForeignKey(Membership, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    kind = models.CharField(max_length=30)
    title = models.CharField(max_length=200)
    body = models.TextField()
    dedupe_key = models.CharField(max_length=200)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [models.UniqueConstraint(fields=['recipient', 'dedupe_key'], name='unique_recipient_notification')]


class ReviewAssessment(models.Model):
    """Human-authored rubric and an immutable-on-publication evidence snapshot."""
    review = models.OneToOneField(PerformanceReview, on_delete=models.PROTECT, related_name='assessment')
    rubric = models.JSONField(default=dict)
    evidence_snapshot = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)


class KnowledgeArticle(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    author = models.ForeignKey(Membership, on_delete=models.PROTECT)
    title = models.CharField(max_length=160)
    summary = models.CharField(max_length=400)
    content = models.TextField()
    tags = models.JSONField(default=list)
    status = models.CharField(max_length=12, choices=[(v, v) for v in ['Draft', 'Published', 'Archived']], default='Draft')
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-id']


class ArticleRevision(models.Model):
    article = models.ForeignKey(KnowledgeArticle, on_delete=models.PROTECT, related_name='revisions')
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    version = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-version']
        constraints = [models.UniqueConstraint(fields=['article', 'version'], name='unique_article_revision')]


class InsightRun(models.Model):
    """An author-private input preview and explicit, bounded AI generation attempt."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    creator = models.ForeignKey(Membership, on_delete=models.PROTECT)
    provider = models.CharField(max_length=20)
    model = models.CharField(max_length=100)
    status = models.CharField(max_length=16, default='Prepared')
    input_snapshot = models.JSONField(default=dict)
    input_hash = models.CharField(max_length=64)
    output = models.JSONField(default=dict)
    error = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']


class ProjectReport(models.Model):
    """A curated project snapshot; published reports are immutable authenticated records."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    creator = models.ForeignKey(Membership, on_delete=models.PROTECT)
    title = models.CharField(max_length=160)
    summary = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    risks = models.TextField(blank=True)
    next_steps = models.TextField(blank=True)
    snapshot = models.JSONField(default=dict)
    status = models.CharField(max_length=12, default='Draft')
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at', '-id']
