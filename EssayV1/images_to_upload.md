# Images to upload to Overleaf

Create a folder named `final_diagram_images` next to `essay_from_toc.tex` in Overleaf, then upload the files below into that folder.

## Required files

| File in Overleaf | Used for |
|---|---|
| `final_diagram_images/ecom_context_map.png` | DDD context map for the e-commerce system. |
| `final_diagram_images/healthcare_case_decomposition.png` | Healthcare DDD practice decomposition. |
| `final_diagram_images/ecom_class_diagram.png` | Summary class diagram generated from the real Django models. |
| `final_diagram_images/ecom_database_mapping.png` | Database-per-service mapping. |
| `final_diagram_images/ecom_ai_pipeline.png` | AI chatbot, RAG, behavior model, and Neo4j pipeline. |
| `final_diagram_images/ecom_system_architecture.png` | Runtime Docker Compose architecture. |
| `final_diagram_images/ecom_gateway_routing.png` | Nginx gateway route mapping. |
| `final_diagram_images/ecom_checkout_sequence.png` | Checkout orchestration sequence. |
| `final_diagram_images/Class_Diagram_E_Commerce.svg` | Visual Paradigm class diagram, included as vector SVG. |
| `final_diagram_images/DataModel_ORM.svg` | Visual Paradigm ORM data model, included as vector SVG. |
| `final_diagram_images/DataModel_ORM_ERD.svg` | Visual Paradigm ERD data model, included as vector SVG. |

## Optional fallback files

The LaTeX macro uses this priority order for the three Visual Paradigm diagrams: SVG first, PDF second, PNG last. Upload these only if you want a fallback:

- `final_diagram_images/Class_Diagram_E_Commerce.pdf` or `final_diagram_images/Class_Diagram_E_Commerce.png`
- `final_diagram_images/DataModel_ORM.pdf` or `final_diagram_images/DataModel_ORM.png`
- `final_diagram_images/DataModel_ORM_ERD.pdf` or `final_diagram_images/DataModel_ORM_ERD.png`

## Compile note

Use `XeLaTeX` on Overleaf because the report uses Vietnamese text through `fontspec`. The project also needs shell escape for SVG conversion; your current log already shows `\write18 enabled`, so shell escape is enabled.
