<?xml version="1.0" encoding="UTF-8"?>
<!--
     show-bundle.xsl - extract all code sections with one code name from a weave.

     Run this stylesheet on weave.xml, passing the required code_name string
     parameter and choosing the result filename with xsltproc's output option.

     The output contains only matching code sections, in article/weave order.
     Each bundle member is the original code section, with an article
     attribute added to identify its source. Explanations are excluded. An
     empty bundle means no matching code sections were found.
-->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <!-- Avoid pretty-printing whitespace into copied code content. -->
    <xsl:output method="xml" encoding="UTF-8" indent="no"/>

    <!-- A sentinel distinguishes an omitted required parameter from empty name. -->
    <xsl:param name="code_name" select="'__CODE_NAME_PARAMETER_REQUIRED__'"/>

    <xsl:template match="/">
        <xsl:if test="$code_name = '__CODE_NAME_PARAMETER_REQUIRED__'">
            <xsl:message terminate="yes">show-bundle.xsl requires --stringparam code_name NAME (use an empty value for the unnamed bundle).</xsl:message>
        </xsl:if>

        <xsl:variable name="canonical-name" select="normalize-space($code_name)"/>
        <xsl:variable name="definitions"
            select="/lp5-weave/articles/article/section[@data-lp5-kind = 'code'][normalize-space(name) = $canonical-name]"/>

        <bundle name="{$canonical-name}">
            <xsl:for-each select="$definitions">
                <!-- Preserve the on-disk code-section representation. -->
                <xsl:text>&#10;  </xsl:text>
                <section data-lp5-kind="code" article="{../@file}">
                    <!-- Format the section metadata, but copy code unchanged. -->
                    <xsl:text>&#10;    </xsl:text>
                    <xsl:copy-of select="name"/>
                    <xsl:text>&#10;    </xsl:text>
                    <xsl:copy-of select="code"/>
                    <xsl:text>&#10;  </xsl:text>
                </section>
            </xsl:for-each>
            <xsl:text>&#10;</xsl:text>
        </bundle>
        <xsl:text>&#10;</xsl:text>
    </xsl:template>
</xsl:stylesheet>
