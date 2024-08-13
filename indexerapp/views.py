from django.shortcuts import render, get_object_or_404
from django.views import View

# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate


from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Manuscripts, AttributeDebate, Content, Formulas, Subjects, RiteNames, ManuscriptMusicNotations, Provenance, Codicology, Layouts, TimeReference, Bibliography, EditionContent, BindingTypes, BindingStyles, BindingMaterials, Colours, Clla, Projects, MSProjects
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType

from django.forms.models import model_to_dict

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from django_serverside_datatable.views import ServerSideDatatableView

from .serializers import *

from dal import autocomplete

from pyzotero import zotero

from django.http import JsonResponse
from rest_framework import viewsets

#for admin url creation:
from django.urls import reverse
import math

#For filtering only specific columns:
from django.db.models import Q
from django_filters import filters
from rest_framework_datatables.django_filters.backends import DatatablesFilterBackend
from rest_framework_datatables.django_filters.filterset import DatatablesFilterSet
from rest_framework_datatables.django_filters.filters import GlobalFilter
from django.db.models import Count


#For assistant:
from django.db import connection
from dubo import generate_sql
import os

#For content importer:
from decimal import Decimal
import json
from django.apps import apps
from django.db import models

from iommi import Page, Form, Table

#For graph generation:
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io

#For TEI:
from xml.etree.ElementTree import Element, SubElement, tostring




#from zotero.forms import get_tag_formset

ZOTERO_library_type = 'group'
#ZOTERO_api_key = 'HhPM6AN8emREftJShQBRITeI' #'5hnxe02vaDuZJ8O4qkUAT6Ty'
#ZOTERO_library_id = 5244710

ZOTERO_api_key = '5hnxe02vaDuZJ8O4qkUAT6Ty'
#ZOTERO_library_id = 12744975
ZOTERO_library_id = 5244710 #group id

class Login(View):
    template = 'login.html'

    def get(self, request):
        form = AuthenticationForm()
        return render(request, self.template, {'form': form})


    def post(self, request):
        form = AuthenticationForm(request.POST)
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return HttpResponseRedirect('/static/page.html?p=manuscripts')
        else:
            return render(request, self.template, {'form': form})

class MainInfoAjaxView(View):
    def get(self, request, *args, **kwargs):
        # Assuming you want to retrieve the username from the currently logged-in user
        username = request.user.get_username()
        
        # You can include more data here if needed
        data = {
            'username': username,
            # Add more key-value pairs as needed
        }

        return JsonResponse(data)


class MSInfoAjaxView(View):
    def get(self, request, *args, **kwargs):
        # Get the manuscript instance using the provided ID (pk)
        manuscript_id = self.request.GET.get('pk')
        instance = get_object_or_404(Manuscripts, id=manuscript_id)

        # Main info
        info = get_obj_dictionary(instance, [])

        #authors_names = [str(author) for author in instance.authors.all()]
        #info['authors']=authors_names

        # Manuscript comments (debate)
        debate = AttributeDebate.objects.filter(content_type__model='manuscripts', object_id=manuscript_id)
        debate_data = []

        # Iterate over each debate object
        for d in debate:
            # Find the Bibliography object associated with the bibliography_id
            bibliography = Bibliography.objects.get(id=d.bibliography_id)
            
            # Create a dictionary with debate details
            debate_dict = {
                'id': d.id,
                'field_name': d.field_name,
                'text': d.text,
                'bibliography': str(bibliography),  # String representation of the Bibliography name
                'bibliography_id': d.bibliography_id 
            }
            
            # Append the dictionary to the debate_data list
            debate_data.append(debate_dict)

        # Create the response dictionary
        data = {
            'manuscript': info,
            'debate': debate_data,  # Convert QuerySet to a list for JSON serialization
        }

        return JsonResponse(data)


class GlobalCharFilter(GlobalFilter, filters.CharFilter):
    pass

class GlobalNumberFilter(GlobalFilter, filters.NumberFilter):
    pass

class CustomDatatablesFilterBackend(DatatablesFilterBackend):
    #help(rest_framework_datatables.django_filters.backends)
    #help(DatatablesFilterBackend)

    def filter_queryset(self, request, queryset, view):
        queryset = super().filter_queryset(request, queryset, view)
        
        where_min = request.query_params.get('where_min')
        where_max = request.query_params.get('where_max')

        print(where_min)
        print(where_min)

        if where_min is not None:
            queryset = queryset.filter(where_in_ms_from__gte=where_min)
        
        if where_max is not None:
            queryset = queryset.filter(where_in_ms_from__lte=where_max)

        return queryset

class ContentGlobalFilter(DatatablesFilterSet):
    """Filter name, artist and genre by name with icontains"""

    'manuscript', 'formula', 'rite', 'rite_name_from_ms', 'formula_text', 'sequence_in_ms', 'where_in_ms_from', 'where_in_ms_to', 'similarity_by_user', 'similarity_levenshtein' 

    manuscript = filters.NumberFilter(lookup_expr='exact')


    #manuscript = GlobalCharFilter(lookup_expr='icontains')
    #formula = GlobalCharFilter(field_name='formula__text', lookup_expr='icontains')
    rite_name_from_ms = GlobalCharFilter(field_name='rite_name_from_ms', lookup_expr='icontains')
    formula_text = GlobalCharFilter(field_name='formula_text', lookup_expr='icontains')
    sequence_in_ms = GlobalCharFilter()
    where_in_ms_from = GlobalNumberFilter(field_name='where_in_ms_from', lookup_expr='gt')
    where_in_ms_to = GlobalNumberFilter(field_name='where_in_ms_to', lookup_expr='lt')

    class Meta:
        model = Content
        fields = '__all__'


class ContentViewSet(viewsets.ModelViewSet):
    queryset = Content.objects.all().order_by('manuscript')
    serializer_class = ContentSerializer

    filter_backends = [CustomDatatablesFilterBackend]
    filterset_class = ContentGlobalFilter

    def count(self, request, queryset):
        return queryset.count()

    """
    def get_queryset(self):
        manuscript_id = self.request.GET.get('manuscript_id', None)
        if manuscript_id:
            return Content.objects.filter(manuscript_id=manuscript_id).order_by('manuscript')
        else:
            return Content.objects.all().order_by('manuscript')
    """

class ManuscriptHandsViewSet(viewsets.ModelViewSet):
    serializer_class = ManuscriptHandsSerializer
    filter_backends = [DatatablesFilterBackend]

    def get_queryset(self):
        is_main_text_param = self.request.query_params.get('is_main_text')
        manuscript_id_param = self.request.query_params.get('ms')
        
        # Convert is_main_text_param to a boolean value
        is_main_text = True if is_main_text_param == "true" else False if is_main_text_param == "false" else None
        
        queryset = ManuscriptHands.objects.all()
        
        # Apply the filter for is_main_text if provided
        if is_main_text is not None:
            queryset = queryset.filter(is_main_text=is_main_text)
        
        # Apply the filter for manuscript_id if provided
        if manuscript_id_param is not None:
            queryset = queryset.filter(manuscript_id=manuscript_id_param)
        
        return queryset

class ManuscriptsViewSet(viewsets.ModelViewSet):
    queryset = Manuscripts.objects.all().order_by('name')
    serializer_class = ManuscriptsSerializer

    filter_backends = [DatatablesFilterBackend]


    def get_queryset(self):
        # Extract ordering parameters from DataTables formatted request
        order_column_index = int(self.request.query_params.get('order[0][column]', 0))
        order_column_name = self.request.query_params.get(f'columns[{order_column_index}][data]', 'name')
        order_direction = self.request.query_params.get('order[0][dir]', 'asc')

        name = self.request.query_params.get('name')
        foreign_id = self.request.query_params.get('foreign_id')
        contemporary_repository_place = self.request.query_params.get('contemporary_repository_place')
        shelfmark = self.request.query_params.get('shelfmark')
        dating = self.request.query_params.get('dating')
        place_of_origins = self.request.query_params.get('place_of_origins')
        main_script = self.request.query_params.get('main_script')
        binding_date = self.request.query_params.get('binding_date')

        # Pobierz wartości zapytań dla minimalnych i maksymalnych wartości
        how_many_columns_min = self.request.query_params.get('how_many_columns_min')
        how_many_columns_max = self.request.query_params.get('how_many_columns_max')
        lines_per_page_min = self.request.query_params.get('lines_per_page_min')
        lines_per_page_max = self.request.query_params.get('lines_per_page_max')
        how_many_quires_min = self.request.query_params.get('how_many_quires_min')
        how_many_quires_max = self.request.query_params.get('how_many_quires_max')

        # Filtering for dating_min and dating_max
        dating_min = self.request.query_params.get('dating_min')
        dating_max = self.request.query_params.get('dating_max')
        binding_date_min = self.request.query_params.get('binding_date_min')
        binding_date_max = self.request.query_params.get('binding_date_max')


        decoration_true = self.request.query_params.get('decoration_true')
        decoration_false = self.request.query_params.get('decoration_false')
        decoration_true = True if decoration_true == "true" else False if decoration_true == "false" else None
        decoration_false = True if decoration_false == "true" else False if decoration_false == "false" else None
        
        
        music_notation_true = self.request.query_params.get('music_notation_true')
        music_notation_false = self.request.query_params.get('music_notation_false')
        music_notation_true = True if music_notation_true == "true" else False if music_notation_true == "false" else None
        music_notation_false = True if music_notation_false == "true" else False if music_notation_false == "false" else None

        
        digitized_true = self.request.query_params.get('digitized_true')
        digitized_false = self.request.query_params.get('digitized_false')
        digitized_true = True if digitized_true == "true" else False if digitized_true == "false" else None
        digitized_false = True if digitized_false == "true" else False if digitized_false == "false" else None










        queryset = Manuscripts.objects.all()
                
                    
        # Apply the filter for name if provided
        if name:
            name_ids = name.split(';')  # Rozdziel wartość name na listę identyfikatorów
            queryset = queryset.filter(id__in=name_ids)  # Przefiltruj wyniki, aby pasowały do identyfikatorów z listy
        if foreign_id:
            queryset = queryset.filter(foreign_id=foreign_id)
        if contemporary_repository_place:
            contemporary_repository_place_ids = contemporary_repository_place.split(';')
            queryset = queryset.filter(contemporary_repository_place__in=contemporary_repository_place_ids)
        if shelfmark:
            shelfmark_ids = shelfmark.split(';')
            queryset = queryset.filter(shelf_mark__in=shelfmark_ids)
        if dating:
            dating_ids = dating.split(';')
            queryset = queryset.filter(dating__in=dating_ids)
        if place_of_origins:
            place_of_origins_ids = place_of_origins.split(';')
            queryset = queryset.filter(place_of_origins__in=place_of_origins_ids)
        if main_script:
            main_script_ids = main_script.split(';')
            queryset = queryset.filter(main_script__in=main_script_ids)
        if binding_date:
            binding_date_ids = binding_date.split(';')
            queryset = queryset.filter(binding_date__in=binding_date_ids)
        


        # Filtruj po minimalnych wartościach, jeśli są dostarczone
        if how_many_columns_min and how_many_columns_min.isdigit():
            queryset = queryset.filter(how_many_columns_mostly__gte=int(how_many_columns_min))
        if lines_per_page_min and lines_per_page_min.isdigit():
            queryset = queryset.filter(lines_per_page_usually__gte=int(lines_per_page_min))
        if how_many_quires_min and how_many_quires_min.isdigit():
            queryset = queryset.filter(how_many_quires__gte=int(how_many_quires_min))

        # Filtruj po maksymalnych wartościach, jeśli są dostarczone
        if how_many_columns_max and how_many_columns_max.isdigit():
            queryset = queryset.filter(how_many_columns_mostly__lte=int(how_many_columns_max))
        if lines_per_page_max and lines_per_page_max.isdigit():
            queryset = queryset.filter(lines_per_page_usually__lte=int(lines_per_page_max))
        if how_many_quires_max and how_many_quires_max.isdigit():
            queryset = queryset.filter(how_many_quires__lte=int(how_many_quires_max))

        if binding_date_min and binding_date_min.isdigit():
            queryset = queryset.filter(Q(binding_date__century_from__gte=int(binding_date_min)) | Q(binding_date__century_to__gte=int(binding_date_min)))

        if binding_date_max and binding_date_max.isdigit():
            queryset = queryset.filter(Q(binding_date__century_from__lte=int(binding_date_max)) | Q(binding_date__century_to__lte=int(binding_date_max)))

        if dating_min and dating_min.isdigit():
            queryset = queryset.filter(Q(dating__century_from__gte=int(dating_min)) | Q(dating__century_to__gte=int(dating_min)))

        if dating_max and dating_max.isdigit():
            queryset = queryset.filter(Q(dating__century_from__lte=int(dating_max)) | Q(dating__century_to__lte=int(dating_max)))


        if decoration_false and not decoration_true:
            queryset = queryset.filter(decorated=False)
        if decoration_true and not decoration_false:
            queryset = queryset.filter(decorated=True)

        if music_notation_false and not music_notation_true:
            queryset = queryset.filter(music_notation=False)
        if music_notation_true and not music_notation_false:
            queryset = queryset.filter(music_notation=True)

        if digitized_false and not digitized_true:
            queryset = queryset.filter(Q(iiif_manifest_url__isnull=True) | Q(iiif_manifest_url__exact=''), Q(links__isnull=True) | Q(links__exact=''))
        if digitized_true and not digitized_false:
            queryset = queryset.filter(Q(iiif_manifest_url__isnull=False) & ~Q(iiif_manifest_url__exact='') | Q(links__isnull=False) & ~Q(links__exact=''))

        #NEW CHECKS:
        foliation = self.request.query_params.get('foliation')
        pagination = self.request.query_params.get('pagination')
        foliation = True if foliation == "true" else False if foliation == "false" else None
        pagination = True if pagination == "true" else False if pagination == "false" else None
        if foliation and not pagination:
            queryset = queryset.filter(foliation_or_pagination="FOLIATION")
        if pagination and not foliation:
            queryset = queryset.filter(foliation_or_pagination="PAGINATION")

        number_of_parchment_folios_min = self.request.query_params.get('number_of_parchment_folios_min')
        number_of_parchment_folios_max = self.request.query_params.get('number_of_parchment_folios_max')
        # Check if number_of_parchment_folios_min is provided and is a digit
        if number_of_parchment_folios_min and number_of_parchment_folios_min.isdigit():
            queryset = queryset.filter(ms_codicology__number_of_parchment_folios__gte=int(number_of_parchment_folios_min))

        # Check if number_of_parchment_folios_max is provided and is a digit
        if number_of_parchment_folios_max and number_of_parchment_folios_max.isdigit():
            queryset = queryset.filter(ms_codicology__number_of_parchment_folios__lte=int(number_of_parchment_folios_max))



        #New true/false values:
        paper_leafs_true = self.request.query_params.get('paper_leafs_true')
        watermarks_true = self.request.query_params.get('watermarks_true')
        is_main_text_true = self.request.query_params.get('is_main_text_true')
        written_above_the_top_line_true = self.request.query_params.get('written_above_the_top_line_true')
        binding_decoration_true = self.request.query_params.get('binding_decoration_true')
        parchment_shrinkage_true = self.request.query_params.get('parchment_shrinkage_true')
        illegible_text_fragments_true = self.request.query_params.get('illegible_text_fragments_true')
        ink_corrosion_true = self.request.query_params.get('ink_corrosion_true')
        copper_corrosion_true = self.request.query_params.get('copper_corrosion_true')
        powdering_or_cracking_paint_layer_true = self.request.query_params.get('powdering_or_cracking_paint_layer_true')
        conservation_true = self.request.query_params.get('conservation_true')
        display_as_main_true = self.request.query_params.get('display_as_main_true')
        
        paper_leafs_false = self.request.query_params.get('paper_leafs_false')
        watermarks_false = self.request.query_params.get('watermarks_false')
        is_main_text_false = self.request.query_params.get('is_main_text_false')
        written_above_the_top_line_false = self.request.query_params.get('written_above_the_top_line_false')
        binding_decoration_false = self.request.query_params.get('binding_decoration_false')
        parchment_shrinkage_false = self.request.query_params.get('parchment_shrinkage_false')
        illegible_text_fragments_false = self.request.query_params.get('illegible_text_fragments_false')
        ink_corrosion_false = self.request.query_params.get('ink_corrosion_false')
        copper_corrosion_false = self.request.query_params.get('copper_corrosion_false')
        powdering_or_cracking_paint_layer_false = self.request.query_params.get('powdering_or_cracking_paint_layer_false')
        conservation_false = self.request.query_params.get('conservation_false')
        display_as_main_false = self.request.query_params.get('display_as_main_false')
        
        paper_leafs_true = True if paper_leafs_true == 'true' else False if paper_leafs_true == 'false' else None
        watermarks_true = True if watermarks_true == 'true' else False if watermarks_true == 'false' else None
        is_main_text_true = True if is_main_text_true == 'true' else False if is_main_text_true == 'false' else None
        written_above_the_top_line_true = True if written_above_the_top_line_true == 'true' else False if written_above_the_top_line_true == 'false' else None
        binding_decoration_true = True if binding_decoration_true == 'true' else False if binding_decoration_true == 'false' else None
        parchment_shrinkage_true = True if parchment_shrinkage_true == 'true' else False if parchment_shrinkage_true == 'false' else None
        illegible_text_fragments_true = True if illegible_text_fragments_true == 'true' else False if binding_decoration_true == 'false' else None
        ink_corrosion_true = True if ink_corrosion_true == 'true' else False if ink_corrosion_true == 'false' else None
        copper_corrosion_true = True if copper_corrosion_true == 'true' else False if copper_corrosion_true == 'false' else None
        powdering_or_cracking_paint_layer_true = True if powdering_or_cracking_paint_layer_true == 'true' else False if powdering_or_cracking_paint_layer_true == 'false' else None
        conservation_true = True if conservation_true == 'true' else False if conservation_true == 'false' else None
        display_as_main_true = True if display_as_main_true == 'true' else False if display_as_main_true == 'false' else None
        
        paper_leafs_false = True if paper_leafs_false == 'true' else False if paper_leafs_false == 'false' else None
        watermarks_false = True if watermarks_false == 'true' else False if watermarks_false == 'false' else None
        is_main_text_false = True if is_main_text_false == 'true' else False if is_main_text_false == 'false' else None
        written_above_the_top_line_false = True if written_above_the_top_line_false == 'true' else False if written_above_the_top_line_false == 'false' else None
        binding_decoration_false = True if binding_decoration_false == 'true' else False if binding_decoration_false == 'false' else None
        parchment_shrinkage_false = True if parchment_shrinkage_false == 'true' else False if parchment_shrinkage_false == 'false' else None
        illegible_text_fragments_false = True if illegible_text_fragments_false == 'true' else False if illegible_text_fragments_false == 'false' else None
        ink_corrosion_false = True if ink_corrosion_false == 'true' else False if ink_corrosion_false == 'false' else None
        copper_corrosion_false = True if copper_corrosion_false == 'true' else False if copper_corrosion_false == 'false' else None
        powdering_or_cracking_paint_layer_false = True if powdering_or_cracking_paint_layer_false == 'true' else False if powdering_or_cracking_paint_layer_false == 'false' else None
        conservation_false = True if conservation_false == 'true' else False if conservation_false == 'false' else None
        display_as_main_false = True if display_as_main_false == 'true' else False if display_as_main_false == 'false' else None

        
        if paper_leafs_false and not paper_leafs_true:
            queryset = queryset.exclude(ms_codicology__number_of_paper_leaves__gt=0)
        if paper_leafs_true and not paper_leafs_false:
            queryset = queryset.filter(ms_codicology__number_of_paper_leaves__gt=0)
            
        if watermarks_false and not watermarks_true:
            queryset = queryset.filter(ms_codicology__watermarks=False)
        if watermarks_true and not watermarks_false:
            queryset = queryset.filter(ms_codicology__watermarks=True)

        if is_main_text_false and not is_main_text_true:
            queryset = queryset.exclude(ms_hands__is_main_text=True)
        if is_main_text_true and not is_main_text_false:
            queryset = queryset.filter(ms_hands__is_main_text=True)

        if written_above_the_top_line_false and not written_above_the_top_line_true:
            queryset = queryset.filter(ms_layouts__written_above_the_top_line=False)
        if written_above_the_top_line_true and not written_above_the_top_line_false:
            queryset = queryset.filter(ms_layouts__written_above_the_top_line=True)

        if binding_decoration_false and not binding_decoration_true:
            queryset = queryset.exclude(ms_binding_decorations__isnull=False)
        if binding_decoration_true and not binding_decoration_false:
            queryset = queryset.filter(ms_binding_decorations__isnull=False)

        if parchment_shrinkage_false and not parchment_shrinkage_true:
            queryset = queryset.filter(ms_condition__parchment_shrinkage=False)
        if parchment_shrinkage_true and not parchment_shrinkage_false:
            queryset = queryset.filter(ms_condition__parchment_shrinkage=True)
        
        if illegible_text_fragments_false and not illegible_text_fragments_true:
            queryset = queryset.filter(ms_condition__illegible_text_fragments=False)
        if illegible_text_fragments_true and not illegible_text_fragments_false:
            queryset = queryset.filter(ms_condition__illegible_text_fragments=True)
        
        if ink_corrosion_false and not ink_corrosion_true:
            queryset = queryset.filter(ms_condition__ink_corrosion=False)
        if ink_corrosion_true and not ink_corrosion_false:
            queryset = queryset.filter(ms_condition__ink_corrosion=True)
        
        if copper_corrosion_false and not copper_corrosion_true:
            queryset = queryset.filter(ms_condition__copper_corrosion=False)
        if copper_corrosion_true and not copper_corrosion_false:
            queryset = queryset.filter(ms_condition__copper_corrosion=True)

        if powdering_or_cracking_paint_layer_false and not powdering_or_cracking_paint_layer_true:
            queryset = queryset.filter(ms_condition__powdering_or_cracking_paint_layer=False)
        if powdering_or_cracking_paint_layer_true and not powdering_or_cracking_paint_layer_false:
            queryset = queryset.filter(ms_condition__powdering_or_cracking_paint_layer=True)

        if conservation_false and not conservation_true:
            queryset = queryset.filter(ms_condition__conservation=False)
        if conservation_true and not conservation_false:
            queryset = queryset.filter(ms_condition__conservation=True)

        if display_as_main_false and not display_as_main_true:
            queryset = queryset.exclude(display_as_main=True)
        if display_as_main_true and not display_as_main_false:
            queryset = queryset.filter(display_as_main=True)

        #New min/max values:
        binding_height_min = self.request.query_params.get('binding_height_min')
        binding_width_min = self.request.query_params.get('binding_width_min')
        written_space_height_min = self.request.query_params.get('written_space_height_min')
        written_space_width_min = self.request.query_params.get('written_space_width_min')
        distance_between_horizontal_ruling_min = self.request.query_params.get('distance_between_horizontal_ruling_min')
        distance_between_vertical_ruling_min = self.request.query_params.get('distance_between_vertical_ruling_min')
        ms_how_many_hands_min = self.request.query_params.get('ms_how_many_hands_min')
        page_size_wh_min = self.request.query_params.get('page_size_wh_min')
        parchment_thickness_min = self.request.query_params.get('parchment_thickness_min')
        binding_height_max = self.request.query_params.get('binding_height_max')
        binding_width_max = self.request.query_params.get('binding_width_max')
        written_space_height_max = self.request.query_params.get('written_space_height_max')
        written_space_width_max = self.request.query_params.get('written_space_width_max')
        distance_between_horizontal_ruling_max = self.request.query_params.get('distance_between_horizontal_ruling_max')
        distance_between_vertical_ruling_max = self.request.query_params.get('distance_between_vertical_ruling_max')
        ms_how_many_hands_max = self.request.query_params.get('ms_how_many_hands_max')
        page_size_wh_max = self.request.query_params.get('page_size_wh_max')
        parchment_thickness_max = self.request.query_params.get('parchment_thickness_max')
        block_size_min = self.request.query_params.get('block_size_min')
        block_size_max = self.request.query_params.get('block_size_max')

        if binding_height_min and binding_height_min.isdigit():
            queryset = queryset.filter(ms_binding__max_height__gte=int(binding_height_min))
        if binding_height_max and binding_height_max.isdigit():
            queryset = queryset.filter(ms_binding__max_height__lte=int(binding_height_max))

        if binding_width_min and binding_width_min.isdigit():
            queryset = queryset.filter(ms_binding__max_width__gte=int(binding_width_min))
        if binding_width_max and binding_width_max.isdigit():
            queryset = queryset.filter(ms_binding__max_width__lte=int(binding_width_max))

        if written_space_height_min and written_space_height_min.isdigit():
            queryset = queryset.filter(ms_layouts__written_space_height_max__gte=int(written_space_height_min))
        if written_space_height_max and written_space_height_max.isdigit():
            queryset = queryset.filter(ms_layouts__written_space_height_max__lte=int(written_space_height_max))

        if written_space_width_min and written_space_width_min.isdigit():
            queryset = queryset.filter(ms_layouts__written_space_width_max__gte=int(written_space_width_min))
        if written_space_width_max and written_space_width_max.isdigit():
            queryset = queryset.filter(ms_layouts__written_space_width_max__lte=int(written_space_width_max))
            
        if distance_between_horizontal_ruling_min and distance_between_horizontal_ruling_min.isdigit():
            queryset = queryset.filter(ms_layouts__distance_between_horizontal_ruling__gte=int(distance_between_horizontal_ruling_min))
        if distance_between_horizontal_ruling_max and distance_between_horizontal_ruling_max.isdigit():
            queryset = queryset.filter(ms_layouts__distance_between_horizontal_ruling__lte=int(distance_between_horizontal_ruling_max))

        if distance_between_vertical_ruling_min and distance_between_vertical_ruling_min.isdigit():
            queryset = queryset.filter(ms_layouts__distance_between_vertical_ruling__gte=int(distance_between_vertical_ruling_min))
        if distance_between_vertical_ruling_max and distance_between_vertical_ruling_max.isdigit():
            queryset = queryset.filter(ms_layouts__distance_between_vertical_ruling__lte=int(distance_between_vertical_ruling_max))

        if ms_how_many_hands_min and ms_how_many_hands_min.isdigit():
            queryset = queryset.annotate(num_hands=Count('ms_hands')).filter(num_hands__gte=int(ms_how_many_hands_min))
        if ms_how_many_hands_max and ms_how_many_hands_max.isdigit():
            queryset = queryset.annotate(num_hands=Count('ms_hands')).filter(num_hands__lte=int(ms_how_many_hands_max))

        if page_size_wh_min and page_size_wh_min.isdigit():
            queryset = queryset.filter(
                Q(ms_codicology__page_size_max_height__gte=int(page_size_wh_min)) &
                Q(ms_codicology__page_size_max_width__gte=int(page_size_wh_min))
            )

        if page_size_wh_max and page_size_wh_max.isdigit():
            queryset = queryset.filter(
                Q(ms_codicology__page_size_max_height__lte=int(page_size_wh_max)) &
                Q(ms_codicology__page_size_max_width__lte=int(page_size_wh_max))
            )

        if parchment_thickness_min and float(parchment_thickness_min):
            queryset = queryset.filter(ms_codicology__parchment_thickness_min__gte=float(parchment_thickness_min))
        if parchment_thickness_max and float(parchment_thickness_max):
            queryset = queryset.filter(ms_codicology__parchment_thickness_max__lte=float(parchment_thickness_max))

        if block_size_min and block_size_min.isdigit():
            queryset = queryset.filter(ms_binding__block_max__gte=int(block_size_min))
        if block_size_max and block_size_max.isdigit():
            queryset = queryset.filter(ms_binding__block_max__lte=int(block_size_max))


        #New select values:
        parchment_colour_select = self.request.query_params.get('parchment_colour_select')
        main_script_select = self.request.query_params.get('main_script_select')
        type_of_the_quire_select = self.request.query_params.get('type_of_the_quire_select')
        script_name_select = self.request.query_params.get('script_name_select')
        ruling_method_select = self.request.query_params.get('ruling_method_select')
        pricking_select = self.request.query_params.get('pricking_select')
        binding_place_of_origin_select = self.request.query_params.get('binding_place_of_origin_select')
        binding_type_select = self.request.query_params.get('binding_type_select')
        binding_style_select = self.request.query_params.get('binding_style_select')
        binding_material_select = self.request.query_params.get('binding_material_select')
        damage_select = self.request.query_params.get('damage_select')
        provenance_place_select = self.request.query_params.get('provenance_place_select')
        title_select = self.request.query_params.get('title_select')
        author_select = self.request.query_params.get('author_select')

        if parchment_colour_select: 
            parchment_colour_select_ids = parchment_colour_select.split(';')
            queryset = queryset.filter(ms_codicology__parchment_colour__in=parchment_colour_select_ids)
        if main_script_select: 
            main_script_select_ids = main_script_select.split(';')
            queryset = queryset.filter(main_script__in=main_script_select_ids)
        if type_of_the_quire_select: 
            type_of_the_quire_select_ids = type_of_the_quire_select.split(';')
            queryset = queryset.filter(ms_quires__type_of_the_quire__in=type_of_the_quire_select_ids)
        if script_name_select: 
            script_name_select_ids = script_name_select.split(';')
            queryset = queryset.filter(ms_hands__script_name__in=script_name_select_ids)
        if ruling_method_select: 
            ruling_method_select_ids = ruling_method_select.split(';')
            queryset = queryset.filter(ms_layouts__ruling_method__in=ruling_method_select_ids)
        if pricking_select: 
            pricking_select_ids = pricking_select.split(';')
            queryset = queryset.filter(ms_layouts__pricking__in=pricking_select_ids)
        if binding_place_of_origin_select: 
            binding_place_of_origin_select_ids = binding_place_of_origin_select.split(';')
            queryset = queryset.filter(ms_binding__place_of_origins__in=binding_place_of_origin_select_ids)
        if binding_type_select: 
            binding_type_select_ids = binding_type_select.split(';')
            queryset = queryset.filter(ms_binding__type_of_binding__in=binding_type_select_ids)
        if binding_style_select: 
            binding_style_select_ids = binding_style_select.split(';')
            queryset = queryset.filter(ms_binding__style_of_binding__in=binding_style_select_ids)
        if binding_material_select: 
            binding_material_select_ids = binding_material_select.split(';')
            queryset = queryset.filter(ms_binding_materials__material__in=binding_material_select_ids)
        if damage_select: 
            damage_select_ids = damage_select.split(';')
            queryset = queryset.filter(ms_condition__damage__in=damage_select_ids)
        if provenance_place_select: 
            provenance_place_select_ids = provenance_place_select.split(';')
            queryset = queryset.filter(ms_provenance__place__in=provenance_place_select_ids)
        if title_select: 
            title_select_ids = title_select.split(';')
            queryset = queryset.filter(ms_bibliography__bibliography__in=title_select_ids)
        if author_select: 
            author_select_ids = author_select.split(';')
            queryset = queryset.filter(ms_bibliography__bibliography__author__in=author_select_ids)

        # Apply ordering to queryset
        if order_direction == 'asc':
            queryset = queryset.order_by(order_column_name)
        else:
            queryset = queryset.order_by(f'-{order_column_name}')


        return queryset.distinct()

class assistantAjaxView(View):

    def get(self, request, *args, **kwargs):
        q = self.request.GET.get('q')
        #print(q)
        sql = self.text_to_sql(q)
        #print(sql)
        answer = self.sql_query(sql)
        json_output = (answer)
        #print(json_output)

        data = {
            'info': json_output
        }

        return JsonResponse(data)

    def text_to_sql(self,text):
        os.environ["DUBO_API_KEY"] = "pk.bb63cda35d47463fb858192bee22510f"
        return generate_sql(text, fast=False)

    def sql_query(self,query):
        with connection.cursor() as cursor:
            cursor.execute(query)
            r = [dict((cursor.description[i][0], value) \
               for i, value in enumerate(row)) for row in cursor.fetchall()]
            cursor.connection.close()
            return r

        return r

class CodicologyAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('pk')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        instance = ms_instance.ms_codicology.first()
        info = get_obj_dictionary(instance,skip_fields)

        # Manuscript comments (debate)
        debate = {}
        if instance:
            debate = AttributeDebate.objects.filter(content_type__model='codicology', object_id=instance.id)

        # Create the response dictionary
        data = {
            'info': info,
            'debate': list(debate.values()),  # Convert QuerySet to a list for JSON serialization
        }

        return JsonResponse(data)


class LayoutsAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_layouts.all()
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        # Create the response dictionary
        data = {
            'data': info_dict,
        }

        return JsonResponse(data)

class DecorationAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_decorations.all()
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        # Create the response dictionary
        data = {
            'data': info_dict,
        }

        return JsonResponse(data)

class QuiresAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_quires.all()
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        # Create the response dictionary
        data = {
            'data': info_dict,
        }

        return JsonResponse(data)

class ConditionAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_condition.all()
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        # Create the response dictionary
        data = {
            'data': info_dict,
        }

        return JsonResponse(data)

class CllaAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_clla.all()
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        # Create the response dictionary
        data = {
            'data': info_dict,
        }

        return JsonResponse(data)

class OriginsAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_origins.all()
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        # Create the response dictionary
        data = {
            'data': info_dict,
        }

        return JsonResponse(data)

class BindingAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_binding.all()
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        #Binding materials:
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_binding_materials.all()
        materials_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        materials_str = ""

        for m in materials_dict:
            materials_str += m['material'] +", "
        materials_str = materials_str[:-2]


        #Binding decorations:
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_binding_decorations.all()
        decorations_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        decorations_str = ""

        for m in decorations_dict:
            decorations_str += m['decoration'] +", "
        decorations_str = decorations_str[:-2]

        data = {}

        if len(info_dict) > 0:
            info_dict[0]['materials'] = materials_str
            info_dict[0]['decorations'] = decorations_str


            # Create the response dictionary
            data = {
                'info': info_dict[0]
            }

        return JsonResponse(data)


class MusicNotationAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_music_notation.all()
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        # Create the response dictionary
        data = {
            'data': info_dict,
        }

        return JsonResponse(data)

class HandsAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_hands.all()
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        # Create the response dictionary
        data = {
            'data': info_dict,
        }

        return JsonResponse(data)

class WatermarksAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_watermarks.all()
        info_dict_original = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]


        watermarks_full = [w.watermark for w in info_queryset]

        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in watermarks_full]

        for idx, obj in enumerate(info_dict):
            obj['where_in_manuscript'] = info_dict_original[idx]['where_in_manuscript']

        # Create the response dictionary
        data = {
            'data': info_dict,
        }

        return JsonResponse(data)

class BibliographyAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)

        #Zotero:
        bibliography = ms_instance.ms_bibliography.all()

        bibliography_full = [b.bibliography for b in bibliography]

        #zot = zotero.Zotero(ZOTERO_library_id, ZOTERO_library_type, ZOTERO_api_key)
        #allItems = zot.items()

        #info_dict = []
        #for b in bibliography:
        #    item = zot.item(b.bibliography.zotero_id, limit=50, content='html', style='acm-siggraph', linkwrap='1')
        #    info_dict.append(item[0])

        skip_fields = ['id', 'manuscript']
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in bibliography_full]

        # Create the response dictionary
        data = {
            'data': info_dict,
        }

        return JsonResponse(data)

class BibliographyExportView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)

        #Zotero:
        bibliography = ms_instance.ms_bibliography.all()

        zot = zotero.Zotero(ZOTERO_library_id, ZOTERO_library_type, ZOTERO_api_key)
        zot.add_parameters(format='bibtex')
        #allItems = zot.items()

        info_str = ""
        for b in bibliography:
            item = zot.item(b.bibliography.zotero_id, limit=50, content='bibtex')
            info_str += item[0] + "\n\n"

        response = HttpResponse(info_str, content_type='application/x-bibtex charset=utf-8')
        return response

class ProvenanceAjaxView(View):
    def get(self, request, *args, **kwargs):
        pk = self.request.GET.get('ms')
        ms_instance = get_object_or_404(Manuscripts, id=pk)
        skip_fields = ['id', 'manuscript']  # Add any other fields to skip
        info_queryset = ms_instance.ms_provenance.all()
        info_dict = [get_obj_dictionary(entry, skip_fields) for entry in info_queryset]

        markers = []
        for p in info_queryset:
            print(p.place.repository_today_eng)
            print(p.place.longitude)
            print(p.place.latitude)
            markers.append({
                'name':p.place.repository_today_eng,
                'lon':p.place.longitude,
                'lat':p.place.latitude,
                })

        # Create the response dictionary
        data = {
            'data': info_dict,
            'markers':markers
        }

        return JsonResponse(data)

class AutocompleteView(View):
    def get(self, request):
        term = request.GET.get('term', '')
        items = Formulas.objects.filter(text__icontains=term)  # You can adjust the filter as needed
        items10 = items[:10]

        return items

        #data = [{'id': item.id, 'text': item.text} for item in items10]
        #return JsonResponse(data, safe=False)

class FormulaAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Formulas.objects.none()

        qs = Formulas.objects.all()

        if self.q:
            qs = qs.filter(text__icontains=self.q)

        return qs

class ContentAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Content.objects.none()

        qs = Content.objects.all()

        if self.q:
            qs = qs.filter(formula_text__icontains=self.q)

        return qs

class ManuscriptsAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Manuscripts.objects.none()

        qs = Manuscripts.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class MSForeignIdAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Pobierz unikalne wartości pola foreign_id, które nie są puste
        qs = Manuscripts.objects.exclude(foreign_id__isnull=True).exclude(foreign_id__exact='').values('foreign_id').distinct()

        # Filtruj wyniki na podstawie wartości wprowadzonej przez użytkownika
        if self.q:
            qs = qs.filter(foreign_id__icontains=self.q)

        return qs

    def get_result_value(self, item):
        return str(item['foreign_id'])

    def get_result_label(self, item):
        return str(item['foreign_id'])

class MSShelfMarkAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Pobierz unikalne wartości pola foreign_id, które nie są puste
        qs = Manuscripts.objects.exclude(shelf_mark__isnull=True).exclude(shelf_mark__exact='').values('shelf_mark').distinct()

        # Filtruj wyniki na podstawie wartości wprowadzonej przez użytkownika
        if self.q:
            qs = qs.filter(shelf_mark__icontains=self.q)

        return qs

    def get_result_value(self, item):
        return str(item['shelf_mark'])

    def get_result_label(self, item):
        return str(item['shelf_mark'])

class MSContemporaryRepositoryPlaceAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Pobierz wszystkie unikalne contemporary_repository_place
        qs = Places.objects.exclude(manuscripts__contemporary_repository_place=None)

        # Filtrowanie wyników na podstawie wprowadzonego zapytania (self.q)
        if self.q:
            # Tworzymy listę warunków dla filtrowania po dowolnym polu
            filters = Q()
            for field in Places._meta.fields:
                if field.get_internal_type() == 'CharField':  # Możemy dodać dodatkowe warunki dla innych typów pól
                    filters |= Q(**{field.name + '__icontains': self.q})  # Tworzymy warunek dla pola typu CharField

            # Zastosowanie filtrowania na podstawie dowolnego pola
            qs = qs.filter(filters)

        return qs

    def get_result_label(self, item):
        # Zwróć etykietę wyniku jako str() z obiektu Places
        return str(item)


class MSDatingAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Pobierz wszystkie unikalne contemporary_repository_place
        qs = TimeReference.objects.exclude(manuscripts_dating__dating=None).distinct()
        # Filtrowanie wyników na podstawie wprowadzonego zapytania (self.q)
        if self.q:
            # Tworzymy listę warunków dla filtrowania po polu 'time_description'
            filters = Q(time_description__icontains=self.q)
            # Zastosujemy filtrowanie na podstawie pola 'time_description'
            qs = qs.filter(filters)

        return qs

    def get_result_label(self, item):
        # Zwróć etykietę wyniku jako str() z obiektu Places
        return str(item)

class MSPlaceOfOriginsAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Pobierz wszystkie unikalne contemporary_repository_place
        qs = Places.objects.exclude(manuscripts_origin__place_of_origins=None).distinct()
        # Filtrowanie wyników na podstawie wprowadzonego zapytania (self.q)
        if self.q:
            # Tworzymy listę warunków dla filtrowania po dowolnym polu
            filters = Q()
            for field in Places._meta.fields:
                if field.get_internal_type() == 'CharField':  # Możemy dodać dodatkowe warunki dla innych typów pól
                    filters |= Q(**{field.name + '__icontains': self.q})  # Tworzymy warunek dla pola typu CharField

            # Zastosowanie filtrowania na podstawie dowolnego pola
            qs = qs.filter(filters)

        return qs

    def get_result_label(self, item):
        # Zwróć etykietę wyniku jako str() z obiektu Places
        return str(item)

class MSMainScriptAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Pobierz wszystkie unikalne contemporary_repository_place
        qs = ScriptNames.objects.exclude(manuscripts__main_script=None).distinct()
        # Filtrowanie wyników na podstawie wprowadzonego zapytania (self.q)
        if self.q:
            # Tworzymy listę warunków dla filtrowania po polu 'name'
            filters = Q(name__icontains=self.q)
            # Zastosujemy filtrowanie na podstawie pola 'name'
            qs = qs.filter(filters)

        return qs

    def get_result_label(self, item):
        # Zwróć etykietę wyniku jako str() z obiektu Places
        return str(item)

class MSBindingDateAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Pobierz wszystkie unikalne contemporary_repository_place
        qs = TimeReference.objects.exclude(manuscripts_binding_date__binding_date=None).distinct()
        # Filtrowanie wyników na podstawie wprowadzonego zapytania (self.q)
        if self.q:
            # Tworzymy listę warunków dla filtrowania po polu 'time_description'
            filters = Q(time_description__icontains=self.q)
            # Zastosujemy filtrowanie na podstawie pola 'time_description'
            qs = qs.filter(filters)

        return qs

    def get_result_label(self, item):
        # Zwróć etykietę wyniku jako str() z obiektu Places
        return str(item)

class ContributorsAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Contributors.objects.none()

        qs = Contributors.objects.all()

        if self.q:
            qs = qs.filter(formula_text__icontains=self.q)

        return qs

class SubjectAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Subjects.objects.none()

        qs = Subjects.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class RiteNamesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return RiteNames.objects.none()

        qs = RiteNames.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs


class ColoursAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Colours.objects.none()

        qs = Colours.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class ScriptNamesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return ScriptNames.objects.none()

        qs = ScriptNames.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class BindingTypesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return BindingTypes.objects.none()

        qs = BindingTypes.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class BindingStylesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return BindingStyles.objects.none()

        qs = BindingStyles.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs

class BindingMaterialsAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return BindingMaterials.objects.none()

        qs = BindingMaterials.objects.all()

        if self.q:
            qs = qs.filter(name__icontains=self.q)

        return qs
    
class BibliographyTitleAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Bibliography.objects.none()

        qs = Bibliography.objects.all()

        if self.q:
            qs = qs.filter(title__icontains=self.q)

        return qs

class BibliographyAuthorAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        # Don't forget to filter out results depending on the visitor !
        if not self.request.user.is_authenticated:
            return Bibliography.objects.none()

        qs = Bibliography.objects.all()

        if self.q:
            qs = qs.filter(author__icontains=self.q)

        return qs

    def get_result_label(self, item):
        return item.author

class PlacesAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Places.objects.none()

        qs = Places.objects.all()

        if self.q:
            qs = qs.filter(
                Q(place_type__icontains=self.q) |
                Q(country_today_eng__icontains=self.q) |
                Q(region_today_eng__icontains=self.q) |
                Q(city_today_eng__icontains=self.q) |
                Q(repository_today_eng__icontains=self.q) |
                Q(country_today_local_language__icontains=self.q) |
                Q(region_today_local_language__icontains=self.q) |
                Q(city_today_local_language__icontains=self.q) |
                Q(repository_today_local_language__icontains=self.q) |
                Q(country_historic_eng__icontains=self.q) |
                Q(region_historic_eng__icontains=self.q) |
                Q(city_historic_eng__icontains=self.q) |
                Q(repository_historic_eng__icontains=self.q) |
                Q(country_historic_local_language__icontains=self.q) |
                Q(region_historic_local_language__icontains=self.q) |
                Q(city_historic_local_language__icontains=self.q) |
                Q(repository_historic_local_language__icontains=self.q) |
                Q(country_historic_latin__icontains=self.q) |
                Q(region_historic_latin__icontains=self.q) |
                Q(city_historic_latin__icontains=self.q) |
                Q(repository_historic_latin__icontains=self.q)
            )

        return qs

        

@method_decorator(csrf_exempt, name='dispatch')
class ContentImportView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            import_result = self.import_content(data)

            return import_result
                #return JsonResponse({'info': 'success'}, status=200)
        except Exception as e:
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)


    def check_foreign_key_existence(self, table_name, foreign_key_value):
        # Sprawdź, czy wartość foreign_key_value istnieje w tabeli o nazwie table_name
        # W tym przykładzie zakładamy, że table_name to nazwa modelu Django
        try:
            model = globals()[table_name.capitalize()]  # Pobierz model na podstawie nazwy
            return model.objects.filter(pk=foreign_key_value).exists()  # Sprawdź istnienie rekordu z danym kluczem głównym
        except KeyError:
            # Obsłuż wyjątek, jeśli nie można odnaleźć modelu o danej nazwie
            return False

    def import_content(self, data):

        content_list = []

        try:
            for row in data:

                for key, value in row.items():
                    if value == '':
                        row[key] = None

                # Convert names to IDs
                new_liturgical_genre_id = None
                if 'liturgical_genre_id' in row:
                    new_liturgical_genre_id = self.get_id_by_name('LiturgicalGenres', row.get('liturgical_genre_id'), 'title')
                
                new_function_id = None
                if 'function_id' in row:
                    new_function_id = self.get_id_by_name('ContentFunctions', row.get('function_id'))
                
                new_subfunction_id = None
                if 'subfunction_id' in row:
                    new_subfunction_id = self.get_id_by_name('ContentFunctions', row.get('subfunction_id'))
                
                new_section_id = None
                if 'section_id' in row:
                    new_section_id = self.get_id_by_name('Sections', row.get('section_id'))
                
                new_subsection_id = None
                if 'subsection_id' in row:
                    new_subsection_id = self.get_id_by_name('Sections', row.get('subsection_id'))

                new_edition_index = None
                if 'edition_index' in row and row.get('edition_index') :
                    print(row.get('edition_index'))
                    parts = row.get('edition_index').split(" c.")
                    bibliography_shortname= parts[0]
                    feast_rite_sequence= parts[1]
                    new_edition_index = self.get_edition_content_id_by_fields('EditionContent', bibliography_shortname, feast_rite_sequence)
                
                if new_liturgical_genre_id == None and row.get('liturgical_genre_id') != None :
                    return JsonResponse({'info': 'error: could not find value "'+row.get('liturgical_genre_id')+'" in table LiturgicalGenres'}, status=200)
                if new_function_id == None and row.get('function_id')  != None :
                    return JsonResponse({'info': 'error: could not find value "'+row.get('function_id') +'" in table ContentFunctions'}, status=200)
                if new_subfunction_id == None and row.get('subfunction_id')  != None :
                    return JsonResponse({'info': 'error: could not find value "'+row.get('subfunction_id') +'" in table ContentFunctions'}, status=200)
                if new_section_id == None and row.get('section_id')  != None :
                    return JsonResponse({'info': 'error: could not find value "'+row.get('section_id') +'" in table Sections'}, status=200)
                if new_subsection_id == None and row.get('subsection_id')  != None :
                    return JsonResponse({'info': 'error: could not find value "'+row.get('subsection_id') +'" in table Sections'}, status=200)
                if new_edition_index == None and row.get('edition_index')  != None :
                    return JsonResponse({'info': 'error: could not find value "'+row.get('edition_index') +'" in table EditionContent'}, status=200)



                row['liturgical_genre_id'] = new_liturgical_genre_id 
                row['function_id'] = new_function_id
                row['subfunction_id'] = new_subfunction_id 
                row['section_id'] = new_section_id
                row['subsection_id'] = new_subsection_id
                row['edition_index'] = new_edition_index

                where_in_ms_from = None
                if 'where_in_ms_from' in row and row['where_in_ms_from'] is not None:
                    where_in_ms_from = Decimal(row['where_in_ms_from'])

                where_in_ms_to = None
                if 'where_in_ms_to' in row and row['where_in_ms_to'] is not None:
                    where_in_ms_to = Decimal(row['where_in_ms_to'])

                    # Sprawdź, czy wartość klucza obcego 'formula_id' jest poprawna
                if 'formula_id' in row and row['formula_id'] is not None:
                    formula_id = row['formula_id']
                    if not self.check_foreign_key_existence('formulas', formula_id):
                        return JsonResponse({'info': f'error: could not find value "{formula_id}" in table formulas'}, status=200)


                content = Content(
                    manuscript_id=row.get('manuscript_id'),
                    formula_id=row.get('formula_id'),
                    rite_id=row.get('rite_id'),
                    rite_name_from_ms=row.get('rite_name_from_ms'),
                    subrite_name_from_ms=row.get('subrite_name_from_ms'),
                    rite_sequence=row.get('rite_sequence_in_the_MS'),
                    formula_text=row.get('formula_text_from_ms'),
                    sequence_in_ms=row.get('formula_sequence_in_ms'),
                    where_in_ms_from=where_in_ms_from,
                    where_in_ms_to=where_in_ms_to,
                    original_or_added=row.get('original_or_added'),
                    liturgical_genre_id=row.get('liturgical_genre_id'),
                    quire_id=row.get('quire_id'),
                    section_id=row.get('section_id'),
                    subsection_id=row.get('subsection_id'),
                    music_notation_id=row.get('music_notation_id'),
                    function_id=row.get('function_id'),
                    subfunction_id=row.get('subfunction_id'),
                    biblical_reference=row.get('biblical_reference'),
                    reference_to_other_items=row.get('reference_to_other_items'),
                    similarity_by_user=row.get('similarity_by_user'),
                    #entry_date=row.get('entry_date'),
                    edition_index_id=row.get('edition_index'),
                    edition_subindex=row.get('edition_subindex'),
                    comments=row.get('comments')
                    # Add more fields as needed
                )

                # Print AutoField values for inspection
                #auto_field_values = {field.attname: getattr(content, field.attname) for field in content._meta.fields if isinstance(field, (models.AutoField, models.BigAutoField))}
                #print(f"AutoField values: {auto_field_values}")

                #content.authors.set(row.get('authors', []))
                content.data_contributor_id = row.get('contributor_id')

                #content.save()
                content_list.append(content)

            ##

            try:
                for content in content_list:
                    content.save()
            except Exception as e:
                failing_row_index = content_list.index(content)
                failing_row = data[failing_row_index]
                return JsonResponse({'info': f'error: could not find value to create foreign key in row {failing_row_index + 1}. ERROR: {str(e)}'}, status=200)

        except Exception as e:
            # Log the error or handle it accordingly
            # Importing none if there is an error in any row
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)


        return JsonResponse({'info': 'success'}, status=200)


    def get_id_by_name(self, model_name, name, field_name='name'):
        model = apps.get_model(app_label='indexerapp', model_name=model_name)
        obj = model.objects.filter(**{f'{field_name}__iexact': name}).first()
        return obj.id if obj else None

    def get_edition_content_id_by_fields(self, model_name, bibliography_shortname, feast_rite_sequence):
        model = apps.get_model(app_label='indexerapp', model_name=model_name)
        obj = model.objects.filter(bibliography__shortname__iexact=bibliography_shortname, feast_rite_sequence=feast_rite_sequence).first()
        return obj.id if obj else None

@method_decorator(csrf_exempt, name='dispatch')
class ManuscriptsImportView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            import_result = self.import_data(data)

            return import_result
            #return JsonResponse({'info': 'success'}, status=200)
        except Exception as e:
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)

    def import_data(self, data):

        content_list = []

        try:
            for row in data:

                for key, value in row.items():
                    if value == '':
                        row[key] = None

                # Convert names to IDs
                new_dating = self.get_id_by_name('TimeReference', row.get('dating'), 'time_description')
                if new_dating == None and row['dating'] != None :
                    return JsonResponse({'info': 'error: could not find value "'+row['dating']+'" in table TimeReference'}, status=200)
                row['dating'] = new_dating 

                print('contemporary repository place in row:')
                print(row['contemporary_repository_place'])

                                

                if row['contemporary_repository_place']:
                    new_contemporary_repository_place = self.get_id_by_name('Places', row.get('contemporary_repository_place'), 'repository_today_local_language')
                    if new_contemporary_repository_place == None and row['contemporary_repository_place'] != None :
                        return JsonResponse({'info': 'error: could not find value "'+row['contemporary_repository_place']+'" in table Places'}, status=200)
                    row['contemporary_repository_place'] = new_contemporary_repository_place 

                print('contemporary repository place in row:')
                print(row['contemporary_repository_place'])                

                print('place_of_origins in row:')
                print(row['place_of_origins'])   

                if row['place_of_origins']:
                    new_place_of_origins = self.get_id_by_name('Places', row.get('place_of_origins'), 'repository_today_eng')
                    if new_place_of_origins == None and row['place_of_origins'] != None :
                        return JsonResponse({'info': 'error: could not find value "'+row['place_of_origins']+'" in table Places'}, status=200)
                    row['place_of_origins'] = new_place_of_origins 
                
                print('place_of_origins in row:')
                print(row['place_of_origins'])   

                if row['main_script']:
                    new_main_script = self.get_id_by_name('ScriptNames', row.get('main_script'), 'name')
                    if new_main_script == None and row['main_script'] != None :
                        return JsonResponse({'info': 'error: could not find value "'+row['main_script']+'" in table ScriptNames'}, status=200)
                    row['main_script'] = new_main_script 
                    
                if row['binding_date']:
                    new_binding_date = self.get_id_by_name('TimeReference', row.get('binding_date'), 'time_description')
                    if new_binding_date == None and row['binding_date'] != None :
                        return JsonResponse({'info': 'error: could not find value "'+row['binding_date']+'" in table TimeReference'}, status=200)
                    row['binding_date'] = new_binding_date 

                if row['binding_place']:
                    new_binding_place = self.get_id_by_name('Places', row.get('binding_place'), 'repository_today_eng')
                    if new_binding_place == None and row['binding_place'] != None :
                        return JsonResponse({'info': 'error: could not find value "'+row['binding_place']+'" in table Places'}, status=200)
                    row['binding_place'] = new_binding_place 

                if row.get('decorated') == 'yes' :
                    row['decorated']=True
                elif row.get('decorated') == 'no' :
                    row['decorated']=False
                elif row.get('decorated') == None :
                    row['decorated']=None
                else:
                    return JsonResponse({'info': 'error: "decorated" can be only "yes", "no" or empty' }, status=200)

                if row.get('music_notation') == 'yes' :
                    row['music_notation']=True
                elif row.get('music_notation') == 'no' :
                    row['music_notation']=False
                elif row.get('music_notation') == None :
                    row['music_notation']=None
                else:
                    return JsonResponse({'info': 'error: "music_notation" can be only "yes", "no" or empty' }, status=200)

                if row.get('display_as_main') == 'yes' :
                    row['display_as_main']=True
                elif row.get('display_as_main') == 'no' :
                    row['display_as_main']=False
                elif row.get('display_as_main') == None :
                    row['display_as_main']=None
                else:
                    return JsonResponse({'info': 'error: "display_as_main" can be only "yes", "no" or empty' }, status=200)



                content = Manuscripts(
                    id = row.get('id'),
                    name = row.get('name'),
                    rism_id = row.get('rism_id'),
                    foreign_id = row.get('foreign_id'),
                    contemporary_repository_place_id = row.get('contemporary_repository_place'),
                    shelf_mark = row.get('shelf_mark'),
                    liturgical_genre_comment = row.get('liturgical_genre_comment'),
                    common_name = row.get('common_name'),
                    dating_id = row.get('dating'),
                    dating_comment = row.get('dating_comment'),
                    place_of_origins_id = row.get('place_of_origins'),
                    place_of_origins_comment = row.get('place_of_origins_comment'),
                    main_script_id = row.get('main_script'),
                    how_many_columns_mostly = row.get('how_many_columns_mostly'),
                    lines_per_page_usually =  row.get('lines_per_page_usually'),
                    how_many_quires = row.get('how_many_quires'),
                    quires_comment = row.get('quires_comment'),
                    foliation_or_pagination = row.get('foliation_or_pagination'),
                    decorated = row.get('decorated'),
                    decoration_comments = row.get('decoration_comments'),
                    music_notation = row.get('music_notation'),
                    music_notation_comments = row.get('music_notation_comments'),
                    binding_date_id = row.get('binding_date'),
                    binding_place_id =  row.get('binding_place'),
                    links = row.get('links'),
                    iiif_manifest_url = row.get('iiif_manifest_url'),

                    form_of_an_item = row.get('form_of_an_item'),
                    connected_ms = row.get('connected_ms'),
                    where_in_connected_ms = row.get('where_in_connected_ms'),
                    general_comment = row.get('general_comment'),
                    additional_url = row.get('additional_url'),
                    display_as_main = row.get('display_as_main'),

                    image =  row.get('image'),

                    data_contributor_id =  row.get('contributor_id'),
                        
                )

                # Print AutoField values for inspection
                #auto_field_values = {field.attname: getattr(content, field.attname) for field in content._meta.fields if isinstance(field, (models.AutoField, models.BigAutoField))}
                #print(f"AutoField values: {auto_field_values}")

                #content.authors.set(row.get('authors', []))
                #content.data_contributor_id = row.get('contributor_id')

                #content.save()
                content_list.append(content)

            for content in content_list:
                content.save()
        
        except Exception as e:
            # Log the error or handle it accordingly
            # Importing none if there is an error in any row
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)


        return JsonResponse({'info': 'success'}, status=200)


    def get_id_by_name(self, model_name, name, field_name='name'):
        model = apps.get_model(app_label='indexerapp', model_name=model_name)
        obj = model.objects.filter(**{f'{field_name}__iexact': name}).first()
        return obj.id if obj else None


@method_decorator(csrf_exempt, name='dispatch')
class TimeReferenceImportView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            import_result = self.import_data(data)
            return import_result
        except Exception as e:
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)

    def import_data(self, data):
        content_list = []

        try:
            for row in data:

                for key, value in row.items():
                    if value == '':
                        row[key] = None

                # Convert names to IDs
                #new_liturgical_genre_id = self.get_id_by_name('LiturgicalGenres', row.get('liturgical_genre_id'), 'title')
                
                #if new_liturgical_genre_id == None and row['liturgical_genre_id'] != None :
                #    return JsonResponse({'info': 'error: could not find value "'+row['liturgical_genre_id']+'" in table LiturgicalGenres'}, status=200)
                
                #row['liturgical_genre_id'] = new_liturgical_genre_id 

                content = TimeReference(
                    time_description = row.get('time_description'),
                    century_from = row.get('century_from'),
                    century_to = row.get('century_to'),
                    year_from = row.get('year_from'),
                    year_to = row.get('year_to'),
                )


                #content.authors.set(row.get('authors', []))
                #content.data_contributor_id = row.get('contributor_id')

                #content.save()
                content_list.append(content)

            for content in content_list:
                content.save()
        
        except Exception as e:
            # Log the error or handle it accordingly
            # Importing none if there is an error in any row
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)


        return JsonResponse({'info': 'success'}, status=200)


    def get_id_by_name(self, model_name, name, field_name='name'):
        model = apps.get_model(app_label='indexerapp', model_name=model_name)
        obj = model.objects.filter(**{f'{field_name}__iexact': name}).first()
        return obj.id if obj else None

@method_decorator(csrf_exempt, name='dispatch')
class EditionContentImportView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            import_result = self.import_data(data)
            return import_result
        except Exception as e:
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)

    def import_data(self, data):
        content_list = []

        try:
            for row in data:

                for key, value in row.items():
                    if value == '':
                        row[key] = None

                # Convert names to IDs
                new_rite_name_standarized = self.get_id_by_name('RiteNames', row.get('rite_name_standarized'), 'name')
                if new_rite_name_standarized == None and row['rite_name_standarized'] != None :
                    return JsonResponse({'info': 'error: could not find value "'+row['rite_name_standarized']+'" in table RiteNames'}, status=200)
                row['rite_name_standarized'] = new_rite_name_standarized 

                new_function = self.get_id_by_name('ContentFunctions', row.get('function'))
                if new_function == None and row['function'] != None :
                    return JsonResponse({'info': 'error: could not find value "'+row['function']+'" in table ContentFunctions'}, status=200)
                row['function'] = new_function
                
                new_subfunction = self.get_id_by_name('ContentFunctions', row.get('subfunction'))
                if new_subfunction == None and row['subfunction'] != None :
                    return JsonResponse({'info': 'error: could not find value "'+row['subfunction']+'" in table ContentFunctions'}, status=200)
                row['subfunction'] = new_subfunction 



                content = EditionContent(
                    bibliography_id = row.get('bibliography_id'),
                    formula_id = row.get('formula_id'),
                    rite_name_standarized_id = row.get('rite_name_standarized'),
                    feast_rite_sequence = row.get('feast_rite_sequence'),
                    subsequence = row.get('subsequence'),
                    page = row.get('page'),
                    function_id = row.get('function'),
                    subfunction_id = row.get('subfunction'),
                )


                #content.authors.set(row.get('authors', []))
                content.data_contributor_id = row.get('contributor_id')

                #content.save()
                content_list.append(content)

            for content in content_list:
                content.save()
        
        except Exception as e:
            # Log the error or handle it accordingly
            # Importing none if there is an error in any row
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)


        return JsonResponse({'info': 'success'}, status=200)


    def get_id_by_name(self, model_name, name, field_name='name'):
        model = apps.get_model(app_label='indexerapp', model_name=model_name)
        obj = model.objects.filter(**{f'{field_name}__iexact': name}).first()
        return obj.id if obj else None



@method_decorator(csrf_exempt, name='dispatch')
class CllaImportView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            import_result = self.import_data(data)
            return import_result
        except Exception as e:
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)

    def import_data(self, data):
        content_list = []

        try:
            for row in data:

                for key, value in row.items():
                    if value == '':
                        row[key] = None

                # Convert names to IDs
                if row.get('dating'):
                    new_dating = self.get_id_by_name('TimeReference', row.get('dating'), 'time_description')
                    if new_dating == None and row['dating'] != None :
                        return JsonResponse({'info': 'error: could not find value "'+row['dating']+'" in table TimeReference'}, status=200)
                    row['dating'] = new_dating 

                """
                new_provenance = 
                
                new_provenance = self.get_id_by_name('Places', row.get('provenance'), 'repository_today_eng')

                if new_provenance == None and row['provenance'] != None :
                    new_provenance = self.get_id_by_name('Places', row.get('provenance'), 'repository_today_eng')

                if new_provenance == None and row['provenance'] != None :
                    return JsonResponse({'info': 'error: could not find value "'+row['provenance']+'" in table Places'}, status=200)
                row['provenance'] = new_provenance 
                """


                content = Clla(
                    manuscript_id = row.get('manuscript_id'),
                    clla_no = row.get('clla_no'),
                    liturgical_genre = row.get('liturgical_genre'),
                    dating_id = row.get('dating'),
                    dating_comment = row.get('dating_comment'),
                    provenance = row.get('provenance'),
                    provenance_comment = row.get('provenance_comment'),
                    comment = row.get('comment'),
                )

                #content.authors.set(row.get('authors', []))
                #content.data_contributor_id = row.get('contributor_id')

                #content.save()
                content_list.append(content)

            for content in content_list:
                content.save()
        
        except Exception as e:
            # Log the error or handle it accordingly
            # Importing none if there is an error in any row
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)


        return JsonResponse({'info': 'success'}, status=200)


    def get_id_by_name(self, model_name, name, field_name='name'):
        model = apps.get_model(app_label='indexerapp', model_name=model_name)
        obj = model.objects.filter(**{f'{field_name}__iexact': name}).first()
        return obj.id if obj else None


@method_decorator(csrf_exempt, name='dispatch')
class PlacesImportView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            import_result = self.import_data(data)
            return import_result
        except Exception as e:
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)

    def import_data(self, data):
        content_list = []

        try:
            for row in data:

                for key, value in row.items():
                    if value == '':
                        row[key] = None


                content = Places(
                    longitude = row.get('longitude'),
                    latitude = row.get('latitude'),

                    place_type = row.get('place_type'),

                    country_today_eng = row.get('country_today_eng'),
                    region_today_eng = row.get('region_today_eng'),
                    city_today_eng = row.get('city_today_eng'),
                    repository_today_eng = row.get('repository_today_eng'),

                    country_today_local_language = row.get('country_today_local_language'),
                    region_today_local_language = row.get('region_today_local_language'),
                    city_today_local_language = row.get('city_today_local_language'),
                    repository_today_local_language = row.get('repository_today_local_language'),

                    country_historic_eng = row.get('country_historic_eng'),
                    region_historic_eng = row.get('region_historic_eng'),
                    city_historic_eng = row.get('city_historic_eng'),
                    repository_historic_eng = row.get('repository_historic_eng'),

                    country_historic_local_language = row.get('country_historic_local_language'),
                    region_historic_local_language = row.get('region_historic_local_language'),
                    city_historic_local_language = row.get('city_historic_local_language'),
                    repository_historic_local_language = row.get('repository_historic_local_language'),

                    country_historic_latin = row.get('country_historic_latin'),
                    region_historic_latin = row.get('region_historic_latin'),
                    city_historic_latin = row.get('city_historic_latin'),
                    repository_historic_latin = row.get('repository_historic_latin'),
                )

                #content.authors.set(row.get('authors', []))
                #content.data_contributor_id = row.get('contributor_id')

                #content.save()
                content_list.append(content)

            for content in content_list:
                content.save()
        
        except Exception as e:
            # Log the error or handle it accordingly
            # Importing none if there is an error in any row
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)


        return JsonResponse({'info': 'success'}, status=200)


    def get_id_by_name(self, model_name, name, field_name='name'):
        model = apps.get_model(app_label='indexerapp', model_name=model_name)
        obj = model.objects.filter(**{f'{field_name}__iexact': name}).first()
        return obj.id if obj else None

@method_decorator(csrf_exempt, name='dispatch')
class RiteNamesImportView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            import_result = self.import_data(data)
            return import_result
        except Exception as e:
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)

    def import_data(self, data):
        content_list = []

        try:
            for row in data:

                for key, value in row.items():
                    if value == '':
                        row[key] = None

                # Convert names to IDs
                new_section = self.get_id_by_name('Sections', row.get('section'), 'name')
                
                if new_section == None and row['section'] != None :
                    return JsonResponse({'info': 'error: could not find value "'+row['section']+'" in table Sections'}, status=200)
                
                row['section'] = new_section

                if row.get('votive') == 'yes' :
                    row['votive']=True
                elif row.get('votive') == 'no' :
                    row['votive']=False
                elif row.get('votive') == None :
                    row['votive']=None
                else:
                    return JsonResponse({'info': 'error: "votive" can be only "yes", "no" or empty' }, status=200)


                content = RiteNames(
                    name = row.get('name'),
                    english_translation  = row.get('english_translation'),
                    section_id  = row.get('section'),
                    votive  = row.get('votive'),
                )


                #content.authors.set(row.get('authors', []))
                #content.data_contributor_id = row.get('contributor_id')

                #content.save()
                content_list.append(content)

            for content in content_list:
                content.save()
        
        except Exception as e:
            # Log the error or handle it accordingly
            # Importing none if there is an error in any row
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)


        return JsonResponse({'info': 'success'}, status=200)


    def get_id_by_name(self, model_name, name, field_name='name'):
        model = apps.get_model(app_label='indexerapp', model_name=model_name)
        obj = model.objects.filter(**{f'{field_name}__iexact': name}).first()
        return obj.id if obj else None

@method_decorator(csrf_exempt, name='dispatch')
class FormulasImportView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            import_result = self.import_data(data)
            return import_result
        except Exception as e:
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)

    def import_data(self, data):
        content_list = []

        try:
            for row in data:

                for key, value in row.items():
                    if value == '':
                        row[key] = None

                # Convert names to IDs

                content = Formulas(
                    id = row.get('id'),
                    co_no  = row.get('co_no'),
                    text  = row.get('text')
                )


                #content.authors.set(row.get('authors', []))
                #content.data_contributor_id = row.get('contributor_id')

                #content.save()
                content_list.append(content)

            for content in content_list:
                content.save()
        
        except Exception as e:
            # Log the error or handle it accordingly
            # Importing none if there is an error in any row
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)


        return JsonResponse({'info': 'success'}, status=200)


    def get_id_by_name(self, model_name, name, field_name='name'):
        model = apps.get_model(app_label='indexerapp', model_name=model_name)
        obj = model.objects.filter(**{f'{field_name}__iexact': name}).first()
        return obj.id if obj else None

@method_decorator(csrf_exempt, name='dispatch')
class BibliographyImportView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            import_result = self.import_data(data)
            return import_result
        except Exception as e:
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)

    def import_data(self, data):
        content_list = []

        try:
            for row in data:

                for key, value in row.items():
                    if value == '':
                        row[key] = None

                # Convert names to IDs
                content = Bibliography(
                    title = row.get('title'),
                    author  = row.get('author'),
                    shortname  = row.get('shortname'),
                    year = row.get('year'),
                    zotero_id  = row.get('zotero_id'),
                    hierarchy  = row.get('hierarchy')
                )


                #content.authors.set(row.get('authors', []))
                #content.data_contributor_id = row.get('contributor_id')

                #content.save()
                content_list.append(content)

            for content in content_list:
                content.save()
        
        except Exception as e:
            # Log the error or handle it accordingly
            # Importing none if there is an error in any row
            return JsonResponse({'info': f'error: {str(e)}'}, status=200)


        return JsonResponse({'info': 'success'}, status=200)


    def get_id_by_name(self, model_name, name, field_name='name'):
        model = apps.get_model(app_label='indexerapp', model_name=model_name)
        obj = model.objects.filter(**{f'{field_name}__iexact': name}).first()
        return obj.id if obj else None


class Index(LoginRequiredMixin, View):
    template = 'index.html'
    login_url = '/login/'

    def get(self, request):
        return HttpResponseRedirect('/static/page.html?p=about')

        #manuscripts = Manuscripts.objects.all()
        #content = Content.objects.all()
        #formulas = Formulas.objects.all()
        
        #return render(request,
        #    self.template,
        #    {
        #        'manuscripts': manuscripts,
        #        #'rites': rites,
        #        'content': content,
        #        'formulas': formulas
        #    }
        #)

class ManuscriptsView(LoginRequiredMixin, View):
    template = 'manuscripts.html'
    login_url = '/login/'

    def get(self, request):

        return HttpResponseRedirect('/static/page.html?p=manuscripts')

        #manuscripts = Manuscripts.objects.all()
        #return render(request, self.template, {'manuscripts': manuscripts})


def get_object_attr_dict(obj):
    if obj is None:
        return None

    #model = obj._meta.model
    info = model_to_dict(obj)

    info_strings = {}
    #Translation model to string values:
    for field_name, value in info.items():
        if hasattr(obj, field_name):
            field = getattr(obj, field_name)
            info_strings[field_name]=str(field)

    return info_strings

def foliation(value):
    if value is None:
        return ""
    valueRnd = math.floor(float(value))
    valueRemaining = float(value) - valueRnd;

    retStr = str(valueRnd)
    if valueRemaining > 0.09 and valueRemaining  < 0.11:
        retStr += 'r'
    elif valueRemaining > 0.19 and valueRemaining  < 0.21:
        retStr += 'v'

    return retStr

def get_obj_dictionary(obj, skip_fields):
    if obj is None:
        return None
    
    obj_dict = model_to_dict(obj)
    
    # Exclude specified fields
    for field in skip_fields:
        obj_dict.pop(field, None)

    info_strings = {}
    #Translation model to string values:
    for field_name, value in obj_dict.items():
        if hasattr(obj, field_name):
            field = getattr(obj, field_name)
            if isinstance(field, bool):
                info_strings[field_name] = "Yes" if field else "No"
            elif field is None:
                info_strings[field_name] = "-"
            elif field_name == 'where_in_ms_from' or field_name == 'where_in_ms_to':
                info_strings[field_name] =foliation(field)
            elif field_name == 'authors':
                info_strings[field_name] = [str(author) for author in obj.authors.all()]
            else:
                info_strings[field_name]=str(field)

    return info_strings

from django.core.paginator import Paginator
from django.http import JsonResponse

"""
class MSContentView(ServerSideDatatableView):
    instance = get_object_or_404(Manuscripts, id=2)
    queryset = instance.ms_content.all()
    columns = ['formula', 'rite']


class MSContentView(View):
    template_name = 'ms_content.html'
    items_per_page = 10  # Adjust this based on your preference

    def get(self, request, pk):
        skip_fields = ['id', 'manuscript']
        instance = get_object_or_404(Manuscripts, id=pk)
        objects = instance.ms_content.all()

        # Paginate the queryset
        paginator = Paginator(objects, self.items_per_page)
        draw = int(request.GET.get('draw', 1))
        print('draw: ', draw)
        start = float(request.GET.get('start', 1))
        print('start: ', start)
        length = float(request.GET.get('length', 1))
        print('length: ', length)
        search = request.GET.get('search', 1)
        print('search: ', search)

        page = math.floor(start/length)+1


        paginated_objects = paginator.page(page)


        obj_dict = [get_obj_dictionary(entry, skip_fields) for entry in paginated_objects]

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {
                'draw': draw,
                'recordsTotal': paginator.num_pages*length,
                "recordsFiltered": paginator.num_pages*length,
                'headers': list(obj_dict[0].keys()),
                'data': obj_dict,
                'total_pages': paginator.num_pages,
                'current_page': paginated_objects.number,
            }
            return JsonResponse(data)

        return render(request, self.template_name, {'obj_dict': obj_dict})
"""

class MSMusicNotationView(View):
    template_name = 'music_notation.html'

    def get(self, request, pk):
        skip_fields = ['id', 'manuscript']
        instance = get_object_or_404(Manuscripts, id=pk)
        music_notation_objects = instance.ms_music_notation.all()
        music_notation = [get_obj_dictionary(entry, skip_fields) for entry in music_notation_objects]

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            data = {
                'headers': list(music_notation[0].keys()),
                'rows': music_notation,
            }
            return JsonResponse(data)

        return render(request, self.template_name, {'music_notation': music_notation})


@method_decorator(csrf_exempt, name='dispatch')
class ManuscriptDetail(LoginRequiredMixin, View):
    template = 'manuscript_detail.html'
    login_url = '/login/'


    def get(self, request, pk):
        return HttpResponseRedirect('/static/page.html?p=manuscripts')


        #instance = get_object_or_404(Manuscripts, id=pk)

        #skip_fields = ['id', 'manuscript', 'entry_date']  # Add any other fields to skip


        #Main info:
        #info = get_obj_dictionary(instance,[])

        #MS Comments:
        #debate = AttributeDebate.objects.filter(content_type=ContentType.objects.get_for_model(Manuscripts), object_id=pk)

        #MS Codicology:
        #codicology = get_obj_dictionary(instance.ms_codicology.first(),skip_fields)

        #Layouts:
        #layouts = instance.ms_layouts.all().values()
        #layouts_objects = instance.ms_layouts.all()
        #layouts = [get_obj_dictionary(entry, skip_fields) for entry in layouts_objects]

        #Music notation
        #music_notation_objects = instance.ms_music_notation.all()
        #music_notation = [get_obj_dictionary(entry, skip_fields) for entry in music_notation_objects]

        #Provenance
        #provenance_objects = instance.ms_provenance.all()
        #provenance = [get_obj_dictionary(entry, skip_fields) for entry in provenance_objects]

        #print('---------------------------------')
        #markers = []
        #for p in provenance_objects:
        #    print(p.place.repository_today_eng)
        #    print(p.place.longitude)
        #    print(p.place.latitude)
        #    markers.append({
        #        'name':p.place.repository_today_eng,
        #        'lon':p.place.longitude,
        #        'lat':p.place.latitude,
        #        })

        #Content
        #content = instance.ms_content.all()


        #Zotero:
        #zotCollection = instance.zoteroCollection
        #if zotCollection is not None:
        #bibliography = instance.ms_bibliography.all()

        #zot = zotero.Zotero(ZOTERO_library_id, ZOTERO_library_type, ZOTERO_api_key)

        #print(zot.key_info())

        #allItems = zot.items()

        #print(allItems)

        #zotItems = []
        #for b in bibliography:
        #    item = zot.item(b.bibliography.zotero_id, limit=50, content='html', style='acm-siggraph', linkwrap='1')
        #    zotItems.append(item[0])


        #zotItems = zot.collection_items(zotCollection, limit=50, content='html', style='acm-siggraph', linkwrap='1')
        #print(zotItems[0])
        #else:
        #    zotItems = ['<p> Empty bibliography </p>']
        
        #return render (request, self.template, {
        #    'manuscript': instance,
        #    'debate': debate,
        #    'info': info, #info_formated
        #    'codicology': codicology,
        #    'layouts': layouts,
        #    'content': content,
        #    'zotero':zotItems,
        #    'music_notation': music_notation,
        #    'provenance': provenance,
        #    'markers': markers
        #    })

def manuscript(request):
    html = '''<html>
        <head>
            <script src="https://cdn.jsdelivr.net/npm/tify@0.29.1/dist/tify.js"></script>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/tify@0.29.1/dist/tify.css">
        </head>
        <body>
            <div id="tify" style="height: 100%"></div>
            <script>
            new Tify({
            container: '#tify',
            manifestUrl: 'https://api.digitale-sammlungen.de/iiif/presentation/v2/bsb00061148/manifest',
            })
            </script>
        </body>
        <html>'''
    return HttpResponse(html)


class TestPage(Page):
    #create_form = Form.create(auto__model=Manuscripts)
    a_table = Table(auto__model=Content, 
        #query_from_indexes=True,
        columns__manuscript__filter__include=True,
        columns__formula__filter__include=True,
        columns__rite__filter__include=True,
        columns__rite_name_from_ms__filter__include=True,
        columns__rite_sequence__filter__include=True,
        columns__formula_text__filter__include=True,
        columns__where_in_ms_from__filter__include=True,
        columns__where_in_ms_to__filter__include=True,
    )

    class Meta:
        title = 'An iommi Manuscripts page!'

class contentCompareGraph(View):

    def get(self, request, *args, **kwargs):
        left = self.request.GET.get('left')
        right = self.request.GET.get('right')

        ms_ids = [left,right]
        category_column = 'formula_id'
        value_column = 'sequence_in_ms'


        # Query the database for data
        data = []
        idx=0
        for ms_id in ms_ids:
            manuscript = Manuscripts.objects.get(id=ms_id)
            content_objects = Content.objects.filter(manuscript_id=ms_id, formula_id__isnull=False).values(category_column, value_column)
            data.append({'Table': str(manuscript), 'Values': list(content_objects)})
            idx+=1
        
        # Create a DataFrame from the fetched data
        df = pd.DataFrame(data)
        
        # Reshape the DataFrame to have a separate row for each 'formula_id'
        reshaped_data = []

        for index, row in df.iterrows():
            for value_pair in row['Values']:
                print("value_pair: "+str(value_pair))
                reshaped_data.append({'Table': row['Table'], 'formula_id': value_pair['formula_id'], 'sequence_in_ms': value_pair['sequence_in_ms']})

        reshaped_df = pd.DataFrame(reshaped_data)
        
        # Create a Slope Chart
        plt.figure(figsize=(20, 40), dpi=150)
        # Plot the lines connecting the points for the same 'formula_id' from different tables
        unique_formula_ids = reshaped_df['formula_id'].unique()
        
        for formula_id in unique_formula_ids:
            values = reshaped_df[reshaped_df['formula_id'] == formula_id]
            plt.plot(values['Table'], values['sequence_in_ms'], marker='o', label=f'formula_id {formula_id}')
        
        # Add labels and title
        plt.xlabel('Table Name')
        plt.ylabel('sequence_in_ms')
        plt.title('Slope Chart Example')
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=45)
        
        # Add a legend
        #plt.legend()
        
        # Save the plot as an image (e.g., PNG format)
        #plt.savefig('static_assets/media/img/'+filename)

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        response = HttpResponse(content_type='image/png')
        
        # Set content of the response using the data from the buffer
        response.write(buf.getvalue())
        
        # Close the buffer to free up resources
        buf.close()
        
        return response



class contentCompareEditionGraph(View):

    def get(self, request, *args, **kwargs):
        left = self.request.GET.get('left')
        right = self.request.GET.get('right')

        ms_ids = [left,right]
        category_column = 'edition_index'
        value_column = 'rite_sequence'


        # Query the database for data
        data = []
        for ms_id in ms_ids:
            manuscript = Manuscripts.objects.get(id=ms_id)
            content_objects = Content.objects.filter(manuscript_id=ms_id, edition_index__isnull=False)
            data.append({'Table': str(manuscript), 'Values': list(content_objects)})

        # Create a DataFrame from the fetched data
        df = pd.DataFrame(data)

        # Reshape the DataFrame to have a separate row for each 'edition_index'
        reshaped_data = []

        for index, row in df.iterrows():
            for content_object in row['Values']:
                edition_index = content_object.edition_index # Assuming edition_index is a ForeignKey field in Content model
                reshaped_data.append({'Table': row['Table'], 'edition_index': str(edition_index), 'rite_sequence': content_object.rite_sequence})

        reshaped_df = pd.DataFrame(reshaped_data)
        
        # Create a Slope Chart
        plt.figure(figsize=(40, 10), dpi=150)  # Transposing the figure size

        # Plot the lines connecting the points for the same 'edition_index' from different tables
        unique_edition_indexs = reshaped_df['edition_index'].unique()

        for edition_index in unique_edition_indexs:
            values = reshaped_df[reshaped_df['edition_index'] == edition_index]
            line = plt.plot(values['rite_sequence'], values['Table'], marker='o', label=f'edition_index {str(edition_index)}')  # Swapping x and y axes
            color = line[0].get_color()  # Retrieve the color of the marker used in the line plot
            
            # Annotate only the last point of each edition_index with its label
            # Calculate the midpoint index
            midpoint_index = len(values) // 2
            midpoint = values.iloc[midpoint_index]
            plt.text(midpoint['rite_sequence'], midpoint['Table'], f'{str(edition_index)}', rotation=33, verticalalignment='top', horizontalalignment='right', fontsize=8, color=color)

        # Add labels and title
        plt.ylabel('Connections')  # Swapping x and y axis labels
        plt.xlabel('rite_sequence')  # Swapping x and y axis labels
        plt.title('Comparison graph')

        # Rotate y-axis labels for better readability
        plt.yticks(rotation=45)

        # Add a legend
        plt.legend()

        # Save the plot as an image (e.g., PNG format)
        # plt.savefig('static_assets/media/img/'+filename)

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)

        response = HttpResponse(content_type='image/png')

        # Set content of the response using the data from the buffer
        response.write(buf.getvalue())

        # Close the buffer to free up resources
        buf.close()
        
        return response

class MSRitesLookupView(View):
    def get(self, request, *args, **kwargs):
        ms_id = request.GET.get('ms')
        manuscript = get_object_or_404(Manuscripts, id=ms_id)

        print("manuscript = "+str(manuscript))

        # Get all content related to the manuscript with non-empty edition_index and rite_sequence fields
        ms_content = Content.objects.filter(manuscript=manuscript, edition_index__isnull=False, rite_sequence__isnull=False)

        sorted_ms_content = ms_content.order_by('rite_sequence')
        #sorted_ms_content = [str(ms_content.edition_index) for ms_content in sorted_ms_content]


        sorted_unique_ms_content = []
        last_name=''
        for content in sorted_ms_content:
            name = str(content.edition_index)
            if name != last_name:
                sorted_unique_ms_content.append(name)
            last_name=name


        # Initialize dictionary to store similar manuscripts data
        similar_manuscripts = {}

        print("ms_content len = "+str(len(ms_content)))

        all_related_manuscript_ids = {}

        # Iterate through each content entry related to the manuscript
        for content in ms_content:
            # Get all manuscripts related to the current content's edition_index
            related_manuscripts = Manuscripts.objects.filter(ms_content__edition_index=content.edition_index).exclude(id=manuscript.id)

            # Initialize list to store edition_index for current content
            edition_index_list = []

            # Iterate through each related manuscript
            for related_ms in related_manuscripts:
                all_related_manuscript_ids[related_ms.id] = related_ms.id

        # Initialize list to store edition_index for current content
        edition_index_list = []

        # Iterate through each related manuscript
        for related_ms_id in all_related_manuscript_ids:

            related_ms = get_object_or_404(Manuscripts, id=related_ms_id)

            ms_info = {
                'manuscript_id': related_ms.id,
                'manuscript_name': str(related_ms),
                'total_edition_index_count': 0,
                'identical_edition_index_count': 0,
                'identical_edition_index_on_same_sequence_count': 0,
                'identical_edition_index_list': '',
                'edition_index_list': '',
            }

            all_related_content = []

            last_name=''
            for content in ms_content:
                # Get content related to the current related manuscript
                related_content = Content.objects.filter(manuscript=related_ms, edition_index=content.edition_index, rite_sequence__isnull=False)
                
                if len(related_content)>0:
                    name = str(related_content[0].edition_index)

                    if name != last_name:
                        ms_info['identical_edition_index_list'] += name + ", "
                        ms_info['identical_edition_index_count'] += 1

                        if related_content[0].rite_sequence == content.rite_sequence :
                            ms_info['identical_edition_index_on_same_sequence_count'] += 1
                    
                    last_name = name

            # Get sorted list of edition_index for the related manuscript
            all_content = Content.objects.filter(manuscript=related_ms, edition_index__isnull=False, rite_sequence__isnull=False)
            sorted_edition_index = all_content.order_by('rite_sequence')#.distinct('edition_index')

            sorted_unique_edition_index = []
            last_name=''
            for content in sorted_edition_index:
                name = str(content.edition_index)
                sequence = content.rite_sequence

                if name != last_name:
                    sorted_unique_edition_index.append(name)
                last_name=name


            # Append data to edition_index_list
            ms_info['edition_index_list'] = ', '.join(sorted_unique_edition_index)
            ms_info['total_edition_index_count'] = len(sorted_unique_edition_index)
            
            # Add data to similar_manuscripts dictionary
            similar_manuscripts[related_ms.id] = ms_info


        data = {
            'ms_content': sorted_unique_ms_content,
            'similar_ms': similar_manuscripts
        }

        return JsonResponse(data)


class ManuscriptTEIView(View):
    def get(self, request, *args, **kwargs):
        ms_id = request.GET.get('ms')
        manuscript = get_object_or_404(Manuscripts, id=ms_id)
        codicology = manuscript.ms_codicology.first()

        #xml_header = '''<?xml-model href="https://raw.githubusercontent.com/msDesc/consolidated-tei-schema/master/msdesc.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>
        #<?xml-model href="https://raw.githubusercontent.com/msDesc/consolidated-tei-schema/master/msdesc.rng" type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>
        #<TEI xmlns="http://www.tei-c.org/ns/1.0" xmlns:tei="http://www.tei-c.org/ns/1.0" xml:id="manuscript_{0}">
        #'''.format(ms_id)


        xml_header = '''<?xml-model href="https://raw.githubusercontent.com/msDesc/consolidated-tei-schema/master/msdesc.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>
        <?xml-model href="https://raw.githubusercontent.com/msDesc/consolidated-tei-schema/master/msdesc.rng" type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>
        '''.format(ms_id)

        xml_nsmap = {'tei':'http://www.tei-c.org/ns/1.0'}
        root = Element("TEI", attrib={'xml:id':'manuscript_{0}'.format(ms_id) })
        root.set('xmlns','http://www.tei-c.org/ns/1.0')
        root.set('xmlns:tei','http://www.tei-c.org/ns/1.0')

        #tei_model = '<?xml-model href="https://raw.githubusercontent.com/msDesc/consolidated-tei-schema/master/msdesc.rng" type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>'
        #root.text = tei_model

        #tei_header = SubElement(root, "teiHeader")
        #tei_header.set("lang", "en")

        file_desc = SubElement(root, "fileDesc")
        title_stmt = SubElement(file_desc, "titleStmt")
        title_element = SubElement(title_stmt, "title")
        title_element.text = str(manuscript.name)

        if manuscript.common_name:
            common_name_element = SubElement(title_stmt, "title", type="collection")
            common_name_element.text = str(manuscript.common_name)

        edition_stmt = SubElement(file_desc, "editionStmt")
        edition_element = SubElement(edition_stmt, "edition")
        edition_element.text = "TEI P5"

        publication_stmt = SubElement(file_desc, "publicationStmt")
        publisher_element = SubElement(publication_stmt, "publisher")
        publisher_element.text = "Special Collections, Bodleian Libraries"

        source_desc = SubElement(file_desc, "sourceDesc")
        ms_desc = SubElement(source_desc, "msDesc", id="manuscript_" + str(ms_id))
        ms_desc.set("lang", "en")

        ms_identifier = SubElement(ms_desc, "msIdentifier")
        shelfmark_element = SubElement(ms_identifier, "idno", type="shelfmark")
        shelfmark_element.text = str(manuscript.shelf_mark)

        title_element = SubElement(ms_desc, "head")
        title_element.text = "Title of the manuscript"

        # Add more elements from the Manuscripts and Codicology models
        if manuscript.dating:
            dating_element = SubElement(ms_desc, "origin")
            orig_date_element = SubElement(dating_element, "origDate")
            orig_date_element.set("calendar", "Gregorian")
            orig_date_element.set("notBefore", str(manuscript.dating.year_from))
            orig_date_element.set("notAfter", str(manuscript.dating.year_to))
            orig_date_element.text = manuscript.dating.time_description

        if manuscript.place_of_origins:
            orig_place_element = SubElement(dating_element, "origPlace")
            country_element = SubElement(orig_place_element, "country")
            country_element.set("key", "place_" + str(manuscript.place_of_origins.id))
            country_element.text = str(manuscript.place_of_origins)


        if codicology:
            phys_desc = SubElement(ms_desc, "physDesc")
            object_desc = SubElement(phys_desc, "objectDesc", form="codex")
            parchment_element = SubElement(object_desc, "supportDesc", material="parch")
            if codicology.number_of_parchment_folios:
                extent_element = SubElement(parchment_element, "extent")
                folios_element = SubElement(extent_element, "measure", type="folios")
                folios_element.text = str(codicology.number_of_parchment_folios)

        # Add more fields from the Codicology model

        xml_content = xml_header + tostring(root, encoding="unicode")  
        return HttpResponse(xml_content, content_type="application/xml")