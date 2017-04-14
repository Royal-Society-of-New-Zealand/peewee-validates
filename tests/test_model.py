import pytest

from peewee_validates import ModelValidator
from peewee_validates import ValidationError

from tests.models import BasicFields
from tests.models import ComplexPerson
from tests.models import Course
from tests.models import Organization
from tests.models import Person
from tests.models import Student


def test_not_instance():
    with pytest.raises(AttributeError):
        ModelValidator(Person)


def test_instance():
    instance = Person()
    validator = ModelValidator(instance)
    valid = validator.validate({'name': 'tim'})
    assert valid
    assert validator.data['name'] == 'tim'


def test_required():
    validator = ModelValidator(Person())
    valid = validator.validate()
    assert not valid
    assert validator.errors['name'] == 'must be provided'


def test_clean():
    class TestValidator(ModelValidator):
        def clean(self, data):
            super().clean(data)
            data['name'] += 'awesome'
            return data

    validator = TestValidator(Person())
    valid = validator.validate({'name': 'tim'})
    assert valid
    assert validator.data['name'] == 'timawesome'


def test_clean_error():
    class TestValidator(ModelValidator):
        def clean(self, data):
            raise ValidationError('required')

    validator = TestValidator(Person())
    valid = validator.validate({'name': 'tim'})
    assert not valid
    assert validator.data['name'] == 'tim'
    assert validator.errors['__base__'] == 'must be provided'


def test_choices():
    validator = ModelValidator(ComplexPerson(name='tim'))

    valid = validator.validate({'organization': 1, 'gender': 'S'})
    assert not valid
    assert validator.errors['gender'] == 'must be one of the choices: M, F'
    assert 'name' not in validator.errors

    valid = validator.validate({'organization': 1, 'gender': 'M'})
    assert valid


def test_default():
    validator = ModelValidator(BasicFields())
    valid = validator.validate()
    assert not valid
    assert validator.data['field1'] == 'Tim'
    assert validator.errors['field2'] == 'must be provided'
    assert validator.errors['field3'] == 'must be provided'


def test_related_required_missing():
    validator = ModelValidator(ComplexPerson(name='tim', gender='M'))

    valid = validator.validate({'organization': 999})
    assert not valid
    assert validator.errors['organization'] == 'unable to find related object'

    valid = validator.validate({'organization': None})
    assert not valid
    assert validator.errors['organization'] == 'must be provided'

    valid = validator.validate()
    assert not valid
    assert validator.errors['organization'] == 'must be provided'


def test_related_optional_missing():
    validator = ModelValidator(ComplexPerson(name='tim', gender='M', organization=1))

    valid = validator.validate({'pay_grade': 999})
    assert not valid
    assert validator.errors['pay_grade'] == 'unable to find related object'

    valid = validator.validate({'pay_grade': None})
    assert valid

    valid = validator.validate()
    assert valid


def test_related_required_int():
    org = Organization.create(name='new1')
    validator = ModelValidator(ComplexPerson(name='tim', gender='M'))
    valid = validator.validate({'organization': org.id})
    assert valid


def test_related_required_instance():
    org = Organization.create(name='new1')
    validator = ModelValidator(ComplexPerson(name='tim', gender='M'))
    valid = validator.validate({'organization': org})
    assert valid


def test_related_required_dict():
    org = Organization.create(name='new1')
    validator = ModelValidator(ComplexPerson(name='tim', gender='M'))
    valid = validator.validate({'organization': {'id': org.id}})
    assert valid


def test_related_required_dict_missing():
    validator = ModelValidator(ComplexPerson(name='tim', gender='M'))
    validator.validate({'organization': {}})
    assert validator.errors['organization'] == 'must be provided'


def test_related_optional_dict_missing():
    validator = ModelValidator(ComplexPerson(name='tim', gender='M', organization=1))
    valid = validator.validate({'pay_grade': {}})
    assert valid


def test_unique():
    person = Person.create(name='tim')

    validator = ModelValidator(Person(name='tim'))
    valid = validator.validate({'gender': 'M'})
    assert not valid
    assert validator.errors['name'] == 'must be a unique value'

    validator = ModelValidator(person)
    valid = validator.validate({'gender': 'M'})
    assert valid


def test_unique_index():
    obj = BasicFields.create(field1='one', field2='two', field3='three')

    validator = ModelValidator(BasicFields(field1='one', field2='two', field3='three'))
    valid = validator.validate()
    assert not valid
    assert validator.errors['field1'] == 'fields must be unique together'
    assert validator.errors['field2'] == 'fields must be unique together'

    validator = ModelValidator(obj)
    valid = validator.validate()
    assert valid


def test_validate_only():
    obj = BasicFields(field1='one')

    validator = ModelValidator(obj)
    valid = validator.validate(only=('field1', ))
    assert valid


def test_save():
    obj = BasicFields(field1='one', field2='124124', field3='1232314')

    validator = ModelValidator(obj)
    valid = validator.validate({'field1': 'updated'})
    assert valid

    validator.save()

    assert obj.id
    assert obj.field1 == 'updated'


def test_m2m_empty():
    validator = ModelValidator(Student(name='tim'))

    valid = validator.validate()
    assert valid

    valid = validator.validate({'courses': []})
    assert valid


def test_m2m_missing():
    validator = ModelValidator(Student(name='tim'))

    valid = validator.validate({'courses': [1, 33]})
    assert not valid
    assert validator.errors['courses'] == 'unable to find related object'


def test_m2m_ints():
    validator = ModelValidator(Student(name='tim'))

    c1 = Course.create(name='course1')
    c2 = Course.create(name='course2')

    valid = validator.validate({'courses': [c1.id, c2.id]})
    print(validator.errors)
    assert valid

    # valid = validator.validate({'courses': c1.id})
    # assert valid


def test_m2m_instances():
    validator = ModelValidator(Student(name='tim'))

    c1 = Course.create(name='course1')
    c2 = Course.create(name='course2')

    valid = validator.validate({'courses': [c1, c2]})
    assert valid

    # valid = validator.validate({'courses': c2})
    # assert not valid


def test_m2m_dicts():
    validator = ModelValidator(Student(name='tim'))

    c1 = Course.create(name='course1')
    c2 = Course.create(name='course2')

    valid = validator.validate({'courses': [{'id': c1.id}, {'id': c2.id}]})
    assert valid

    valid = validator.validate({'courses': {'id': c1.id}})
    assert not valid
    assert validator.errors['courses'] == 'unable to find related object'


def test_m2m_dicts_blank():
    validator = ModelValidator(Student(name='tim'))

    valid = validator.validate({'courses': [{}, {}]})
    print(validator.errors)
    assert valid

    valid = validator.validate({'courses': {}})
    assert not valid
    assert validator.errors['courses'] == 'unable to find related object'


def test_m2m_save():
    obj = Student(name='tim')
    validator = ModelValidator(obj)

    c1 = Course.create(name='course1')
    c2 = Course.create(name='course2')

    valid = validator.validate({'courses': [c1, c2]})
    assert valid

    validator.save()

    assert obj.id
    assert c1 in obj.courses
    assert c2 in obj.courses


def test_m2m_save_blank():
    obj = Student(name='tim')
    validator = ModelValidator(obj)

    valid = validator.validate({'courses': [{}, {}]})
    assert valid

    validator.save()

    assert obj.id
