Python field cross-references
=============================

.. py:module:: mod

.. py:class:: A

.. py:function:: separate(value)

   :param value: A value.
   :type value: A
   :rtype: A

.. py:function:: inline(value)

   :param A value: A value.
   :rtype: mod.submod.A

.. py:function:: overridden(value)
   :module: mod.submod

   :param A value: A value.
   :rtype: A

.. py:function:: restored()

   :rtype: A

.. py:function:: precedence(value)

   :param A value: A value.
   :rtype: :py:class:`A`

.. py:function:: marked(value)

   :param value: A value.
   :type value: :py:class:`local <.A>`

.. py:function:: compound(value)

   :param value: A value.
   :type value: list[A] or (mod.submod.A, ~mod.A)

.. py:class:: Outer

   .. py:class:: A

   .. py:class:: Inner

      .. py:class:: A

      .. py:method:: nested(value)

         :param A value: A value.
         :rtype: A

   .. py:method:: restored()

      :rtype: A

   .. py:attribute:: value

      :type: A

.. py:function:: outside()

   :rtype: A

.. py:module:: mod.submod

.. py:class:: A

.. py:function:: separate(value)

   :param value: A value.
   :type value: A
   :rtype: A

.. py:function:: inline(value)

   :param A value: A value.
   :rtype: mod.A

.. py:attribute:: value

   :type: A

.. py:currentmodule:: None

.. py:class:: A
