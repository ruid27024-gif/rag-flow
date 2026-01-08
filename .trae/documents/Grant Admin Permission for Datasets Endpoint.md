I have researched the codebase and identified the necessary changes to grant super admin permissions for the `/datasets` endpoint.

Here is the implementation plan:

1.  **Modify `api/db/services/knowledgebase_service.py`**:
    *   Update the `get_list` method signature to include an `admin_bypass` parameter (defaulting to `False`).
    *   Adjust the query logic in `get_list`: if `admin_bypass` is `True`, skip the permission filtering (which currently restricts results to the user's own or team's datasets) and only filter by `status=VALID`.

2.  **Modify `api/apps/sdk/dataset.py`**:
    *   Import the `AdminUser` model from `api.db.db_models`.
    *   In the `list_datasets` function:
        *   Check if the current `tenant_id` (user ID) exists in the `AdminUser` table.
        *   If the user is an admin:
            *   Skip the permission pre-checks for `id` and `name` filters.
            *   Call `KnowledgebaseService.get_list` with `admin_bypass=True`.

This approach ensures that admin users can list and search all datasets in the system, bypassing standard ownership and team permission restrictions.