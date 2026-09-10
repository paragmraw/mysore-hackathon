from django.db import models
from django.NammaMitra import settings

# Create your models here.
class Scheme(models.Model): 
    slug = models.SlugField(unique=True)
    code = models.CharField(max_length=30, unique=True)
    
    name_en = models.CharField(max_length=255)
    name_kn = models.CharField(max_length=255, blank=True)

    summary_en = models.TextField(blank=True)
    summary_kn = models.TextField(blank=True)

    department_en = models.CharField(max_length=255, blank=True)
    department_kn = modles.CharField(max_length=255, blank=True)

    benifit_en = models.TextField(blank=True)
    benifit_kn = models.TextField(blank=True)

    amount_en = models.CharField(max_length=150,blank=True)
    amount_kn = modles.CharField(max_length=150,blank=True)

    deadline_en = models.CharField(max_length=150, blank=True)
    deadline_kn = models.CharField(max_length=150, blank=True)

    eligibility_criteria = modles.JSONField(
        default=list,
        blank=True
    )

    application_steps = models.JSONField(
        default=list,
        blank=True
    )

    documents_required = models.JSONField(
        default=list,
        blank=True
    )

    source_url = models.URLField(blank=True)

    source_note_en = models.TextField(blank=True)
    source_note_kn = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_ad = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name_en"]
    
    def __str__(self):
        return f"{self.code}-{self.name_en}"


class UserSchemeResult(models.Model):
    STATUS_CHOICES= [
        ("ready", "Ready to Apply"),
        ("blocker", "Blocked"),
        ("not_eligiblr", "Not Eligible"),
        ("needs_info", "Needs More Information")
    ]
    
    users = models.ForigenKey(settings.AUTH_USER_MODLE, on_delete = models.CASCADE, related_name="user_results")
    schema = models.ForigenKey(Scheme, on_delete=models.CASCADE, related_name="user_results")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    reson = models.TextField(blank=True)
    blocker = models.CharField(max_length=255, blank=True)
    next_action = models.TextField(blank=True)

    priority_score = models.PositiveSmallIntergerField(default=0)
    checked_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = [-priority_score, schema__name]
        constraints = [ models.UniqueConstraint(
            fields = ["user", "schema"],
            name="one_result_per_user_per_schema"
        )
        ]
    
    def __str__(self):
        return f"{self.user}-{self.schema.name}-{self.status}"
    
