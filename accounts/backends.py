from django.contrib.auth import backends
from django.contrib.auth import get_user_model


class EmployeeNumberOrUsernameBackend(backends.ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # Пробуем найти по номеру сотрудника
            user = UserModel.objects.get(employee_number=username)
        except UserModel.DoesNotExist:
            try:
                # Если не нашли по номеру, пробуем по username
                user = UserModel.objects.get(username=username)
            except UserModel.DoesNotExist:
                return None

        if user.check_password(password):
            return user
        return None