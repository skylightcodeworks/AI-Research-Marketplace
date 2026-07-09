from rest_framework import serializers


class CompanySearchSerializer(serializers.Serializer):
    """Serializer for company search request."""

    company_name = serializers.CharField(
        required=False, allow_blank=True, help_text="Search by company name"
    )
    domains = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated list of domains (e.g., google.com, microsoft.com)",
    )
    locations_included = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated locations to include (e.g., United States, Germany)",
    )
    locations_excluded = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated locations to exclude",
    )
    employees_min = serializers.IntegerField(
        required=False, min_value=1, help_text="Minimum number of employees"
    )
    employees_max = serializers.IntegerField(
        required=False, help_text="Maximum number of employees"
    )
    industries = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of Apollo industry IDs for is_any_of (see INDUSTRIES_LIST)",
    )
    industries_exclude = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of Apollo industry IDs for is_none_of (see INDUSTRIES_LIST)",
    )
    organization_job_titles = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated org job titles (e.g., software, engineer)",
    )
    organization_job_locations = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated org job locations (e.g., lahore, karachi)",
    )
    lookalike_organization_ids = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated lookalike organization IDs",
    )
    revenue_min = serializers.IntegerField(
        required=False, min_value=0, help_text="Minimum revenue in millions USD"
    )
    revenue_max = serializers.IntegerField(
        required=False, help_text="Maximum revenue in millions USD"
    )
    organization_keyword = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated organization keyword tags (e.g., caster, software)",
    )
    organization_keyword_exclude = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated organization keyword tags to exclude",
    )
    employee_ranges = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Semicolon-separated employee ranges (e.g., "1,10; 11,50")',
    )
    funding_stages = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Comma-separated funding stages (e.g., Seed, Series A)",
    )
    job_titles = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of job titles to filter contacts by",
    )
    seniorities = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of seniority levels to filter contacts by",
    )
    page = serializers.IntegerField(
        required=False, default=1, min_value=1, help_text="Page number"
    )
    per_page = serializers.IntegerField(
        required=False,
        default=25,
        min_value=1,
        max_value=100,
        help_text="Results per page (max 100)",
    )


class CompanySerializer(serializers.Serializer):
    """Serializer for company response."""

    id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    primary_domain = serializers.CharField(read_only=True, allow_null=True)
    logo_url = serializers.CharField(read_only=True, allow_null=True)
    industry = serializers.CharField(read_only=True, allow_null=True)
    estimated_num_employees = serializers.IntegerField(read_only=True, allow_null=True)
    city = serializers.CharField(read_only=True, allow_null=True)
    state = serializers.CharField(read_only=True, allow_null=True)
    country = serializers.CharField(read_only=True, allow_null=True)
    linkedin_url = serializers.CharField(read_only=True, allow_null=True)
    founded_year = serializers.IntegerField(read_only=True, allow_null=True)
    annual_revenue = serializers.IntegerField(read_only=True, allow_null=True)
    annual_revenue_printed = serializers.CharField(read_only=True, allow_null=True)


class CompanySearchResponseSerializer(serializers.Serializer):
    """Serializer for search response."""

    companies = CompanySerializer(many=True)
    total_count = serializers.IntegerField()
    page = serializers.IntegerField()
    per_page = serializers.IntegerField()


class PeopleSearchSerializer(serializers.Serializer):
    """Serializer for people/contacts search request."""

    organization_id = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Apollo organization ID to get contacts from",
    )
    organization_ids = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of Apollo organization IDs",
    )
    domains = serializers.CharField(
        required=False, allow_blank=True, help_text="Comma-separated company domains"
    )
    job_titles = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of job titles to filter by",
    )
    seniorities = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of seniority levels to filter by",
    )
    page = serializers.IntegerField(
        required=False, default=1, min_value=1, help_text="Page number"
    )
    per_page = serializers.IntegerField(
        required=False,
        default=25,
        min_value=1,
        max_value=100,
        help_text="Results per page (max 100)",
    )


class PersonSerializer(serializers.Serializer):
    """Serializer for person/contact response."""

    id = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True, allow_null=True)
    last_name = serializers.CharField(read_only=True, allow_null=True)
    name = serializers.CharField(read_only=True, allow_null=True)
    email = serializers.CharField(read_only=True, allow_null=True)
    title = serializers.CharField(read_only=True, allow_null=True)
    seniority = serializers.CharField(read_only=True, allow_null=True)
    city = serializers.CharField(read_only=True, allow_null=True)
    state = serializers.CharField(read_only=True, allow_null=True)
    country = serializers.CharField(read_only=True, allow_null=True)
    linkedin_url = serializers.CharField(read_only=True, allow_null=True)
    phone_numbers = serializers.ListField(read_only=True, allow_null=True)
    organization_name = serializers.CharField(read_only=True, allow_null=True)


class PeopleSearchResponseSerializer(serializers.Serializer):
    """Serializer for people search response."""

    people = PersonSerializer(many=True)
    total_count = serializers.IntegerField()
    page = serializers.IntegerField()
    per_page = serializers.IntegerField()
